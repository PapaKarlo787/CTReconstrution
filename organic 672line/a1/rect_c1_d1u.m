% 01.05.2026
%
% rect_c3_det1u.m
% Чтение ('c3_det1u.mat', 'A6') из c3_det1u.m (Cu, Au, 2026_04_22, Detector 1: 140 kV, low)
% Полоски выровнены
% A6 размером 512 x 342
% Выделение прямоугольников на изображении
% Рисование прямоугольников с монотонным фоном
% Коор-ты и Среднее в прямоугольниках - как rect_c3_det4u.m
% Threshold = 0.45
% Cu, Au: Запись в файл для plot_c3_det1u.m
% 
%
% 02.05.2026
%
% rect_c3_d1u.m
% Чтение ('c3_d1u.mat', 'A6') из c3_d1u.m (Al 2026_05_02, Detector 1: 140 kV, low)
% Aluminium
%
% Threshold = 0.4 --> BW04, Threshold = 0.6 --> BW06
%
% Aluminium: Запись в файл для plot_c3_d1u.m
%
% Прямоугольники в c3_d1u.m самые темные (Detector 1: 140 kV, low)
% поэтому:
% Rect --> rect_c3_d1u.txt для rect_c3_d3u.m (Detector 3)
%
% fileID = fopen('Rect_c3_d1u.txt', 'w'); % Rect(1:4, x y w h)
% fprintf(fileID, '%d %d %d %d\n', Rect'); % Rect' - вид матрицы как >>Rect, то есть x y w h - столбцы
% fclose(fileID);
%
%
%
% 02.05.2026
%
% rect_c5_d1u.m
% Чтение ('c5_d1u.mat', 'A6') из c5_d1u.m (Al 2026_05_02, Detector 1: 140 kV, low)
% Cu
%
% Threshold = 0.4 --> BW04, Threshold = 0.6 --> BW06
%
% Cu: Запись в файл для plot_c5_d1u.m
%
% Прямоугольники в c5_d1u.m самые темные (Detector 1: 140 kV, low)
% поэтому:
% Rect --> rect_c5_d1u.txt для rect_c5_d3u.m (Detector 3)
%
% fileID = fopen('rect_c5_d1u.txt', 'w'); % Rect(1:4, x y w h)
% fprintf(fileID, '%d %d %d %d\n', Rect'); % Rect' - вид матрицы как >>Rect, то есть x y w h - столбцы
% fclose(fileID);
% При чтении 'rect_c5_d1u.txt' в другом m-файле снова надо Rect = Rect'
%
%

%
% 02.05.2026
%
% rect_c1_d1u.m
% Чтение ('c1_d1u.mat', 'A6') из c1_d1u.m (Pb 2026_05_02, Detector 1: 140 kV, low)
% Pb
%
% Threshold = 0.4 --> BW04, Threshold = 0.6 --> BW06
%
% Pb: Запись в файл для plot_c1_d1u.m
%
% Прямоугольники в c1_d1u.m самые темные (Detector 1: 140 kV, low)
% поэтому:
% Rect --> rect_c1_d1u.txt для rect_c1_d3u.m (Detector 3)
%
% fileID = fopen('rect_c1_d1u.txt', 'w'); % Rect(1:4, x y w h)
% fprintf(fileID, '%d %d %d %d\n', Rect'); % Rect' - вид матрицы как >>Rect, то есть x y w h - столбцы
% fclose(fileID);
% При чтении 'rect_c1_d1u.txt' в другом m-файле снова надо Rect = Rect'
%
%


close all
clear all




A1 = load('c1_d1u.mat'); % из c1_d1u.m
A6 = A1.CD1; 

sza1 = size(A6);  % 512 x 342
h1   = sza1(1);
len3 = sza1(2);


k1 = 1;
figure(k1), imshow(A6);


%BW = edge(A6);
BW04 = im2bw(A6, 0.45); % Threshold = 0.45
BW04 = ~BW04; % invert
k1 = 2;
figure(k1), imshow(BW04);


stats = regionprops(BW04); % получение свойств объектов

% отображение BW с нарисованными прямоугольниками
k1 = 3;
figure(k1), imshow(BW04);
hold on;
for i = 1:numel(stats)
    rectangle('Position', stats(i).BoundingBox, 'Linewidth', 1, 'EdgeColor', 'r'); %, 'LineStyle', '--');
end
hold off;


% отображение Изображения с автоматически нарисованными прямоугольниками
k1 = 4;
figure(k1), imshow(A6);
hold on;
for i = 1:numel(stats)
  rectangle('Position', stats(i).BoundingBox, 'Linewidth', 1, 'EdgeColor', 'r'); %, 'LineStyle', '--');
end
hold off;



% отображение Изображения с нарисованными прямоугольниками - заужены для 
% нахождения средних величин монотонных участков

% stats(i).BoundingBox --> x y w h
% Самые темные нижние 2 





% Pb 0.5 mm
Rect(1, 1) = round(stats(1).BoundingBox(1) + 10); % x
Rect(1, 2) = round(stats(1).BoundingBox(2) + 4); % y
Rect(1, 3) = round(stats(1).BoundingBox(3) - 18); % w
Rect(1, 4) = round(stats(1).BoundingBox(4) - 8); % h

% Pb 1 mm
Rect(2, 1) = round(stats(2).BoundingBox(1) + 5); % x
Rect(2, 2) = round(stats(2).BoundingBox(2) + 2); % y
Rect(2, 3) = round(stats(2).BoundingBox(3) - 12); % w
Rect(2, 4) = round(stats(2).BoundingBox(4) - 8); % h

% Pb 0.2 mm
Rect(3, 1) = round(stats(3).BoundingBox(1) + 7); % x
Rect(3, 2) = round(stats(3).BoundingBox(2) + 3); % y
Rect(3, 3) = round(stats(3).BoundingBox(3) - 31); % w
Rect(3, 4) = round(stats(3).BoundingBox(4) - 8); % h

% Pb 0.1 mm
Rect(4, 1) = round(stats(4).BoundingBox(1) + 8); % x
Rect(4, 2) = round(stats(4).BoundingBox(2) + 4); % y
Rect(4, 3) = round(stats(4).BoundingBox(3) - 22); % w
Rect(4, 4) = round(stats(4).BoundingBox(4) - 10); % h

% Pb 0.3 mm
Rect(5, 1) = round(stats(5).BoundingBox(1) + 8); % x
Rect(5, 2) = round(stats(5).BoundingBox(2) + 5); % y
Rect(5, 3) = round(stats(5).BoundingBox(3) - 25); % w
Rect(5, 4) = round(stats(5).BoundingBox(4) - 12); % h


k1 = 5;
figure(k1), imshow(A6);
sh_text = 12;
hold on;
  for i = 1:5
    rectangle('Position', Rect(i, :), 'EdgeColor', 'r');
    str_i = int2str(i);
    if(i==10) sh_text = 18;  end
    figure(k1), text(Rect(i, 1) - sh_text, Rect(i, 2), str_i, 'Color', 'r');
  end
hold off;
figure(k1), title('Нумерация из stats(i).BoundingBox');



% A61 - A65

% Pb 0.5 mm
x = Rect(1, 1);
y = Rect(1, 2);
w = Rect(1, 3);
h = Rect(1, 4);
A61 = A6(y:y+h, x:x+w);

clear x y w h
% Pb 1 mm
x = Rect(2, 1);
y = Rect(2, 2);
w = Rect(2, 3);
h = Rect(2, 4);
A62 = A6(y:y+h, x:x+w);

clear x y w h
% Pb 0.2 mm
x = Rect(3, 1);
y = Rect(3, 2);
w = Rect(3, 3);
h = Rect(3, 4);
A63 = A6(y:y+h, x:x+w);

clear x y w h
% Pb 0.1 mm
x = Rect(4, 1);
y = Rect(4, 2);
w = Rect(4, 3);
h = Rect(4, 4);
A64 = A6(y:y+h, x:x+w);

clear x y w h
% Pb 0.3 mm
x = Rect(5, 1);
y = Rect(5, 2);
w = Rect(5, 3);
h = Rect(5, 4);
A65 = A6(y:y+h, x:x+w);


% Pb
d6(1) = 0.01;  % cm
d6(2) = 0.02;  % 
d6(3) = 0.03;  % 
d6(4) = 0.05;  %
d6(5) = 0.1;   %
% Экспериментальные данные
mA6(1) = mean(mean(A64));  % 0.01 cm
mA6(2) = mean(mean(A63));  % 0.02 cm
mA6(3) = mean(mean(A65));  % 0.03 cm
mA6(4) = mean(mean(A61));  % 0.05 cm
mA6(5) = mean(mean(A62));  % 1 cm


% Pb, Запись в файл для plot_c1_d1u.m
if(0)
Pb_04(1, :) = d6(:);
Pb_04(2, :) = mA6(:);
fileID = fopen('Pb_rect_c1_d1u.txt', 'w'); % c1_d1u
fprintf(fileID, '%f %f\n', Pb_04);
fclose(fileID);
end


% Запись Rect() в файл для rect_c1_d3u.m
if(0)
fileID = fopen('rect_c1_d1u.txt', 'w');  % Rect(1:4, x y w h)
fprintf(fileID, '%d %d %d %d\n', Rect'); % Rect' в rect_c1_d1u.txt выглядит правильно 
                                         % в rect_c1_d3u.m снова Rect = Rect' 
fclose(fileID);
end








