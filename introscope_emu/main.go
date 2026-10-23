package main

import (
	"bufio"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"image"
	"image/color"
	"math"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"

	"golang.org/x/image/tiff"
)

type Vec [3]float64

func (a Vec) add(b Vec) Vec { return Vec{a[0] + b[0], a[1] + b[1], a[2] + b[2]} }
func (a Vec) sub(b Vec) Vec { return Vec{a[0] - b[0], a[1] - b[1], a[2] - b[2]} }
func (a Vec) mul(k float64) Vec {
	return Vec{a[0] * k, a[1] * k, a[2] * k}
}
func (a Vec) dot(b Vec) float64 { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] }
func (a Vec) cross(b Vec) Vec {
	return Vec{
		a[1]*b[2] - a[2]*b[1],
		a[2]*b[0] - a[0]*b[2],
		a[0]*b[1] - a[1]*b[0],
	}
}
func (a Vec) length() float64 { return math.Sqrt(a.dot(a)) }

type Triangle struct{ A, B, C Vec }

type Mesh struct {
	Triangles []Triangle
	Min, Max  Vec
}

type ObjectConfig struct {
	Name   string  `json:"name"`
	SizeMM Vec     `json:"size_mm"`
	MuMM   float64 `json:"mu_mm"`
}

type SensorConfig struct {
	DistanceMM float64 `json:"distance_mm"`
	AngleDeg   float64 `json:"angle_deg"`
	Reverse    bool    `json:"reverse_channels"`
}

type ScanConfig struct {
	Output   string         `json:"output"`
	SourceMM Vec            `json:"source_mm"`
	Sensors  []SensorConfig `json:"sensors"`
}

type Config struct {
	STL          string         `json:"stl"`
	EnergyKeV    float64        `json:"energy_kev"`
	BeltWidthMM  float64        `json:"belt_width_mm"`
	BeltLengthMM float64        `json:"belt_length_mm"`
	ScanStepMM   float64        `json:"scan_step_mm"`
	SamplesX     int            `json:"samples_x"`
	SamplesY     int            `json:"samples_y"`
	Workers      int            `json:"workers"`
	Objects      []ObjectConfig `json:"objects"`
	Scans        []ScanConfig   `json:"scans"`
}

type Object struct {
	Triangles []Triangle
	MuMM      float64
	Name      string
}

type Sensor struct {
	Center Vec
	Along  Vec
}

func loadSTL(path string) (Mesh, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Mesh{}, err
	}

	var triangles []Triangle

	// Двоичный STL.
	if len(data) >= 84 {
		n := binary.LittleEndian.Uint32(data[80:84])
		if n > 0 && uint64(len(data)) == 84+uint64(n)*50 {
			readVec := func(offset int) Vec {
				var v Vec
				for i := 0; i < 3; i++ {
					bits := binary.LittleEndian.Uint32(data[offset+4*i:])
					v[i] = float64(math.Float32frombits(bits))
				}
				return v
			}
			triangles = make([]Triangle, 0, n)
			for i := uint32(0); i < n; i++ {
				p := 84 + int(i)*50 + 12
				triangles = append(triangles, Triangle{
					readVec(p), readVec(p + 12), readVec(p + 24),
				})
			}
		}
	}

	// Текстовый STL.
	if len(triangles) == 0 {
		var vertices []Vec
		scanner := bufio.NewScanner(strings.NewReader(string(data)))
		for scanner.Scan() {
			fields := strings.Fields(scanner.Text())
			if len(fields) != 4 || !strings.EqualFold(fields[0], "vertex") {
				continue
			}
			var v Vec
			for i := 0; i < 3; i++ {
				v[i], err = strconv.ParseFloat(fields[i+1], 64)
				if err != nil {
					return Mesh{}, fmt.Errorf("координата STL: %w", err)
				}
			}
			vertices = append(vertices, v)
		}
		if err := scanner.Err(); err != nil {
			return Mesh{}, err
		}
		if len(vertices) == 0 || len(vertices)%3 != 0 {
			return Mesh{}, fmt.Errorf("STL не содержит корректных треугольников")
		}
		for i := 0; i < len(vertices); i += 3 {
			triangles = append(triangles, Triangle{
				vertices[i], vertices[i+1], vertices[i+2],
			})
		}
	}

	mesh := Mesh{Triangles: triangles, Min: triangles[0].A, Max: triangles[0].A}
	for _, t := range triangles {
		if t.B.sub(t.A).cross(t.C.sub(t.A)).length() == 0 {
			return Mesh{}, fmt.Errorf("STL содержит вырожденный треугольник")
		}
		for _, v := range [...]Vec{t.A, t.B, t.C} {
			for k := 0; k < 3; k++ {
				if math.IsNaN(v[k]) || math.IsInf(v[k], 0) {
					return Mesh{}, fmt.Errorf("STL содержит недопустимую координату")
				}
				mesh.Min[k] = math.Min(mesh.Min[k], v[k])
				mesh.Max[k] = math.Max(mesh.Max[k], v[k])
			}
		}
	}
	for k := 0; k < 3; k++ {
		if mesh.Min[k] == mesh.Max[k] {
			return Mesh{}, fmt.Errorf("STL имеет нулевой размер по оси %d", k)
		}
	}
	return mesh, nil
}

func makeObjects(c Config, mesh Mesh) ([]Object, error) {
	var maxX, maxY float64
	for _, spec := range c.Objects {
		for _, size := range spec.SizeMM {
			if size <= 0 {
				return nil, fmt.Errorf("%s: размер должен быть > 0", spec.Name)
			}
		}
		if spec.MuMM <= 0 {
			return nil, fmt.Errorf("%s: mu_mm должен быть > 0", spec.Name)
		}
		maxX = math.Max(maxX, spec.SizeMM[0])
		maxY = math.Max(maxY, spec.SizeMM[1])
	}
	if maxX > c.BeltWidthMM || maxY > c.BeltLengthMM {
		return nil, fmt.Errorf("образцы не помещаются на ленте")
	}

	result := make([]Object, len(c.Objects))
	type rect struct{ minX, maxX, minY, maxY float64 }
	positions := make([]rect, len(c.Objects))

	for i, spec := range c.Objects {
		t := 0.5
		if len(c.Objects) > 1 {
			t = float64(i) / float64(len(c.Objects)-1)
		}
		cx := maxX/2 + t*(c.BeltWidthMM-maxX)
		cy := maxY/2 + t*(c.BeltLengthMM-maxY)
		positions[i] = rect{
			cx - spec.SizeMM[0]/2, cx + spec.SizeMM[0]/2,
			cy - spec.SizeMM[1]/2, cy + spec.SizeMM[1]/2,
		}
		for j := 0; j < i; j++ {
			a, b := positions[i], positions[j]
			if a.minX < b.maxX && b.minX < a.maxX &&
				a.minY < b.maxY && b.minY < a.maxY {
				return nil, fmt.Errorf("образцы %d и %d пересекаются", j, i)
			}
		}

		scale := Vec{
			spec.SizeMM[0] / (mesh.Max[0] - mesh.Min[0]),
			spec.SizeMM[1] / (mesh.Max[1] - mesh.Min[1]),
			spec.SizeMM[2] / (mesh.Max[2] - mesh.Min[2]),
		}
		transform := func(p Vec) Vec {
			return Vec{
				positions[i].minX + (p[0]-mesh.Min[0])*scale[0],
				positions[i].minY + (p[1]-mesh.Min[1])*scale[1],
				(p[2] - mesh.Min[2]) * scale[2],
			}
		}
		obj := Object{
			Triangles: make([]Triangle, len(mesh.Triangles)),
			MuMM:      spec.MuMM,
			Name:      spec.Name,
		}
		for k, tri := range mesh.Triangles {
			obj.Triangles[k] = Triangle{
				transform(tri.A), transform(tri.B), transform(tri.C),
			}
		}
		result[i] = obj
	}
	return result, nil
}

func makeSensors(scan ScanConfig) ([]Sensor, error) {
	result := make([]Sensor, len(scan.Sensors))
	for i, s := range scan.Sensors {
		if s.DistanceMM <= 0 {
			return nil, fmt.Errorf("сенсор %d: расстояние должно быть > 0", i)
		}
		a := s.AngleDeg * math.Pi / 180
		n := a + math.Pi

		center := scan.SourceMM.add(Vec{
			s.DistanceMM * math.Cos(a), 0, s.DistanceMM * math.Sin(a),
		})
		normal := Vec{math.Cos(n), 0, math.Sin(n)}
		if normal.dot(scan.SourceMM.sub(center)) <= 0 {
			return nil, fmt.Errorf("сенсор %d направлен лицевой стороной от источника", i)
		}
		along := Vec{-normal[2], 0, normal[0]}
		if s.Reverse {
			along = along.mul(-1)
		}
		result[i] = Sensor{center, along}
	}
	return result, nil
}

// Возвращает расстояние от начала единичного луча до треугольника.
func hitTriangle(origin, direction Vec, t Triangle, limit float64) (float64, bool) {
	const eps = 1e-9
	e1, e2 := t.B.sub(t.A), t.C.sub(t.A)
	p := direction.cross(e2)
	det := e1.dot(p)
	if math.Abs(det) < eps {
		return 0, false
	}
	inv := 1 / det
	q := origin.sub(t.A)
	u := q.dot(p) * inv
	if u < -eps || u > 1+eps {
		return 0, false
	}
	r := q.cross(e1)
	v := direction.dot(r) * inv
	if v < -eps || u+v > 1+eps {
		return 0, false
	}
	distance := e2.dot(r) * inv
	return distance, distance > eps && distance < limit-eps
}

func pathLength(source, target Vec, obj Object, scanY float64) (float64, error) {
	delta := target.sub(source)
	limit := delta.length()
	if limit == 0 {
		return 0, fmt.Errorf("источник совпал с пикселем")
	}
	direction := delta.mul(1 / limit)

	// Объект движется по -Y. Эквивалентно сдвинуть луч по +Y
	// относительно неподвижных треугольников STL.
	origin := source.add(Vec{0, scanY, 0})

	var hits []float64
	for _, tri := range obj.Triangles {
		if distance, ok := hitTriangle(origin, direction, tri, limit); ok {
			hits = append(hits, distance)
		}
	}
	sort.Float64s(hits)

	// Общее ребро соседних треугольников — одна точка пересечения.
	unique := hits[:0]
	for _, h := range hits {
		if len(unique) == 0 || math.Abs(h-unique[len(unique)-1]) > 1e-6 {
			unique = append(unique, h)
		}
	}
	if len(unique) == 1 {
		return 0, nil // касание поверхности
	}
	if len(unique)%2 != 0 {
		return 0, fmt.Errorf("%s: нечётное число пересечений STL (%d)",
			obj.Name, len(unique))
	}
	var length float64
	for i := 0; i < len(unique); i += 2 {
		length += unique[i+1] - unique[i]
	}
	return length, nil
}

func render(c Config, scan ScanConfig, objects []Object) (*image.Gray16, error) {
	sensors, err := makeSensors(scan)
	if err != nil {
		return nil, err
	}
	const channels = 64
	const pitchMM = 1.5125
	const pixelYMM = 3.0

	width := len(sensors) * channels
	height := int(math.Ceil(c.BeltLengthMM/c.ScanStepMM)) + 1
	img := image.NewGray16(image.Rect(0, 0, width, height))

	workers := c.Workers
	if workers == 0 {
		workers = runtime.NumCPU()
	}
	rows := make(chan int, workers*2)
	var wg sync.WaitGroup
	var firstErr error
	var once sync.Once

	for worker := 0; worker < workers; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for row := range rows {
				scanY := float64(row) * c.ScanStepMM
				for col := 0; col < width; col++ {
					s := sensors[col/channels]
					channel := col % channels
					var sum float64

					for a := 0; a < c.SamplesX; a++ {
						x := (float64(channel)-31.5+
							(float64(a)+0.5)/float64(c.SamplesX)-0.5) * pitchMM
						for b := 0; b < c.SamplesY; b++ {
							y := ((float64(b)+0.5)/float64(c.SamplesY) -
								0.5) * pixelYMM
							target := s.Center.add(s.Along.mul(x)).add(Vec{0, y, 0})

							var opticalDepth float64
							for _, obj := range objects {
								length, err := pathLength(
									scan.SourceMM, target, obj, scanY,
								)
								if err != nil {
									once.Do(func() { firstErr = err })
									continue
								}
								opticalDepth += obj.MuMM * length
							}
							sum += math.Exp(-opticalDepth)
						}
					}

					// 65535 — луч без ослабления; 0 — полное ослабление.
					transmission := sum / float64(c.SamplesX*c.SamplesY)
					img.SetGray16(col, row, color.Gray16{
						Y: uint16(math.Round(65535 * transmission)),
					})
				}
			}
		}()
	}
	for row := 0; row < height; row++ {
		rows <- row
	}
	close(rows)
	wg.Wait()

	if firstErr != nil {
		return nil, firstErr
	}
	return img, nil
}

func main() {
	path := "config.json"
	if len(os.Args) > 1 {
		path = os.Args[1]
	}
	data, err := os.ReadFile(path)
	if err != nil {
		panic(err)
	}
	var c Config
	if err := json.Unmarshal(data, &c); err != nil {
		panic(err)
	}
	if c.EnergyKeV != 36 || c.BeltWidthMM <= 0 ||
		c.BeltLengthMM <= 0 || c.ScanStepMM <= 0 ||
		c.SamplesX <= 0 || c.SamplesY <= 0 ||
		c.Workers < 0 || len(c.Objects) == 0 || len(c.Scans) != 2 {
		panic("проверьте параметры config.json")
	}
	if c.Scans[0].Output == c.Scans[1].Output {
		panic("выходные TIFF должны иметь разные имена")
	}

	mesh, err := loadSTL(c.STL)
	if err != nil {
		panic(err)
	}
	objects, err := makeObjects(c, mesh)
	if err != nil {
		panic(err)
	}
	for _, scan := range c.Scans {
		if scan.Output == "" || len(scan.Sensors) == 0 {
			panic("не задан output или sensors")
		}
		img, err := render(c, scan, objects)
		if err != nil {
			panic(err)
		}
		file, err := os.Create(scan.Output)
		if err != nil {
			panic(err)
		}
		encodeErr := tiff.Encode(file, img, nil)
		closeErr := file.Close()
		if encodeErr != nil {
			panic(encodeErr)
		}
		if closeErr != nil {
			panic(closeErr)
		}
		fmt.Printf("%s: %d × %d, 16 бит\n",
			scan.Output, img.Bounds().Dx(), img.Bounds().Dy())
	}
}
