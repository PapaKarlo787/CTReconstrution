#pragma once
#include <fstream>
#include <vector>
#include <cstdint>
#include <stdexcept>
#include <limits>

#pragma pack(push, 1)

struct BMPFileHeader {
	uint16_t bfType = 0x4D42;
	uint32_t bfSize = 0;
	uint16_t bfReserved1 = 0;
	uint16_t bfReserved2 = 0;
	uint32_t bfOffBits = 54;
};

struct BMPInfoHeader {
	uint32_t biSize = 40;
	int32_t  biWidth = 0;
	int32_t  biHeight = 0;
	uint16_t biPlanes = 1;
	uint16_t biBitCount = 24;
	uint32_t biCompression = 0;
	uint32_t biSizeImage = 0;
	int32_t  biXPelsPerMeter = 2835;
	int32_t  biYPelsPerMeter = 2835;
	uint32_t biClrUsed = 0;
	uint32_t biClrImportant = 0;
};

#pragma pack(pop)

void saveBMP(const char* fn, const std::vector<uint8_t>& gray, int width, int height) {
	int rowSize = width * 3;
	int padding = (4 - rowSize % 4) % 4;
	int stride = rowSize + padding;

	BMPFileHeader fileHeader;
	BMPInfoHeader infoHeader;

	infoHeader.biWidth = width;
	infoHeader.biHeight = height;
	infoHeader.biSizeImage = stride * height;

	fileHeader.bfSize =
		sizeof(BMPFileHeader) +
		sizeof(BMPInfoHeader) +
		infoHeader.biSizeImage;

	std::ofstream file(fn, std::ios::binary);

	if (!file) {
		throw std::runtime_error("cannot create BMP file");
	}

	file.write(reinterpret_cast<const char*>(&fileHeader), sizeof(fileHeader));
	file.write(reinterpret_cast<const char*>(&infoHeader), sizeof(infoHeader));

	uint8_t pad[3] = { 0, 0, 0 };

	for (int y = height - 1; y >= 0; --y) {
		for (int x = 0; x < width; ++x) {
			uint8_t v = gray[y * width + x];
			uint8_t bgr[3] = { v, v, v };
			file.write(reinterpret_cast<const char*>(bgr), 3);
		}
		file.write(reinterpret_cast<const char*>(pad), padding);
	}
}

static void writeTIFFEntry(std::ofstream& f, uint16_t tag, uint16_t type, uint32_t count, uint32_t value) {
	f.write((char*)&tag, 2);
	f.write((char*)&type, 2);
	f.write((char*)&count, 4);
	f.write((char*)&value, 4);
}

void saveTIFF16(const char* fn, const std::vector<uint16_t>& gray, int width, int height) {

	uint64_t imageBytes64 = static_cast<uint64_t>(width) * static_cast<uint64_t>(height) * 2;
	uint32_t imageBytes = static_cast<uint32_t>(imageBytes64);
	uint32_t imageOffset = 8;
	uint32_t ifdOffset = imageOffset + imageBytes;
	const uint16_t TYPE_SHORT = 3;
	const uint16_t TYPE_LONG = 4;
	const uint16_t entryCount = 10;
	const uint16_t magic = 42;
	const uint32_t zero = 0;
	std::ofstream file(fn, std::ios::binary);

	file.put('I');
	file.put('I');

	file.write((char*)&magic, 2);
	file.write((char*)&ifdOffset, 4);

	for (int y = 0; y < height; ++y) {
		for (int x = 0; x < width; ++x) {
			uint16_t v = gray[y * width + x];
			file.write((char*)&v, 2);
		}
	}

	file.write((char*)&entryCount, 2);
	writeTIFFEntry(file, 256, TYPE_LONG, 1, static_cast<uint32_t>(width));
	writeTIFFEntry(file, 257, TYPE_LONG, 1, static_cast<uint32_t>(height));
	writeTIFFEntry(file, 258, TYPE_SHORT, 1, 16);
	writeTIFFEntry(file, 259, TYPE_SHORT, 1, 1);
	writeTIFFEntry(file, 262, TYPE_SHORT, 1, 1);
	writeTIFFEntry(file, 273, TYPE_LONG, 1, imageOffset);
	writeTIFFEntry(file, 277, TYPE_SHORT, 1, 1);
	writeTIFFEntry(file, 278, TYPE_LONG, 1, static_cast<uint32_t>(height));
	writeTIFFEntry(file, 279, TYPE_LONG, 1, imageBytes);
	writeTIFFEntry(file, 339, TYPE_SHORT, 1, 1);
	file.write((char*)&zero, 4);
}