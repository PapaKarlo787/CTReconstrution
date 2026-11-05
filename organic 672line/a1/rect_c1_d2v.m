% 01.05.2026
%
% rect_c3_det2u.m
%
% Чтение ('c3_det2u.mat', 'A6') из c3_det2u.m (Cu, Au, 2026_04_22, Detector 2: 200 kV, low)
% Полоски выровнены
% A6 размером 512 x 342
% 
% Выделение прямоугольников на изображении
% Рисование прямоугольников с монотонным фоном
%
% 02.05.2026
%
% rect_c3_d2u.m
% Чтение ('c3_d2u.mat', 'A6') из c3_d2u.m (Al 2026_05_02, Detector 2: 200 kV, low)
% Aluminium
%
% Threshold любой --> bad, т.к. Прямоугольники слишком светлые.
% Берем координаты из rect_c3_d1u.m - Чтение ('rect_c3_d1u.txt')
% Добавляем y
%
% Aluminium: Запись в файл для plot_c3_d2u.m
%
%
% 02.05.2026
%
% rect_c5_d2u.m
% Чтение ('c5_d2u.mat', 'A6') из c5_d2u.m (Cu 2026_05_02, Detector 2: 200 kV, low)
% Cu
%
% Берем координаты из rect_c5_d1u.m - Чтение ('rect_c5_d1u.txt')
%
% Cu: Запись в файл для plot_c5_d2u.m
%
%
%
% 02.05.2026
%
% Pb
% rect_c1_d2u.m
% Чтение ('c1_d2u.mat', 'A6') из c1_d2u.m (Pb 2026_05_02, Detector 2: 200 kV, low)
%
% Берем координаты из rect_c1_d1u.m - Чтение ('rect_c1_d1u.txt')
%
% Pb: Запись в файл для plot_c1_d2u.m
%
%
% 12.05.2026
% plot_c1_d2v.m  (det2: 200 kV, low)
% Pb: Запись в файл для plot_c1_d2v.m
% Запись фона для plot_c1_d2v.m
%
%


close all
clear all




A1 = load('c1_d2u.mat'); % из c1_d2u.m
A6 = A1.CD1; 

sza1 = size(A6);  % 512 x 342
h1   = sza1(1);
len3 = sza1(2);


k1 = 1;
figure(k1), imshow(A6);


% Rect
% Чтение файла (rect_c1_d1v.m)
fileID = fopen('rect_c1_d1v.txt', 'r');
Rect = fscanf(fileID, '%d %d %d %d', [4, inf]);
fclose(fileID);

Rect = Rect';

sh_y = 193; % сдвиг по y вниз

Rect(:, 2) = Rect(:, 2) + sh_y;


k1 = 5;
figure(k1), imshow(A6);
sh_text = 12;
hold on;
  for i = 1:6
    rectangle('Position', Rect(i, :), 'EdgeColor', 'r');
    str_i = int2str(i);
    if(i==10) sh_text = 18;  end
    figure(k1), text(Rect(i, 1) - sh_text, Rect(i, 2), str_i, 'Color', 'r');
  end
hold off;
figure(k1), title('Нумерация int2str(i) где rectangle(Rect(i, :))');



% A61 - A66

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

clear x y w h
% Background
x = Rect(6, 1);
y = Rect(6, 2);
w = Rect(6, 3);
h = Rect(6, 4);
A66 = A6(y:y+h, x:x+w);


% Pb
d6(1) = 0;
d6(2) = 0.01;  % cm
d6(3) = 0.02;  % 
d6(4) = 0.03;  % 
d6(5) = 0.05;  %
d6(6) = 0.1;   %

% Экспериментальные данные
mA6(1) = mean(mean(A66)); % 0
mA6(2) = mean(mean(A64)); % 0.01 cm
mA6(3) = mean(mean(A63)); % 0.02 cm
mA6(4) = mean(mean(A65)); % 0.03 cm
mA6(5) = mean(mean(A61)); % 0.05 cm
mA6(6) = mean(mean(A62)); % 0.1 cm


% Pb, Запись в файл для plot_c1_d2v.m
if(0)
Pb_04(1, :) = d6(:);
Pb_04(2, :) = mA6(:);
fileID = fopen('Pb_rect_c1_d2v.txt', 'w'); % c1_d2v
fprintf(fileID, '%f %f\n', Pb_04);
fclose(fileID);
end


