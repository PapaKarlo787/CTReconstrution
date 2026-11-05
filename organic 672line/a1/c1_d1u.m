% 24.04.2026
%
% Выравнивание столбцов
%
% Pb
% a1_d1u.m
% боковые 1:6 DM из 1:11 DM
%
% B10 = rot90(A10); % Поворот на 90 градусов CCW
% Выравнивание строк
% CD1 = rot90(RD1, 3); % Поворот на 270 градусов CCW, т.е. обратно
%
% A16 = uint16(round(CD1*65535));
% imwrite(A16, 'c1_d1u.tif');
%
% save('c1_d1u.mat', 'CD1');
% Concatenate arrays - c1u_all.m
%



close all
clear all


% Detector 1

A1 = load('a1_d1u.mat'); % 512 x 342
A10 = A1.RD1;

k1 = 3;
figure(k1), imshow(A10);
figure(k1), title('Detector 1');



% Выравнивание столбцов

B10 = rot90(A10); % Поворот на 90 градусов CCW, а потом выранивание строк
%k1 = 4;
%figure(k1), imshow(B10);

sza1 = size(B10);  % 342 x 512
h1 = sza1(1);      % 342


% Выравнивание строк, как в a3_det1u.m 

wid3 = 512;  % wid3 вместо len3

xlim01 = [1 wid3]; % [1 512]
ylim01 = [0.4 1];

A34 = B10; % size(A34) = 342 512

%s1 = 330; % № строки для графика 22.

% строки для определения среднего строк внутри dh
dh = 20;
h3 = 130; %150;
h4 = h3 + dh;

t1 = 40; t2 = 280; % t2 = 270; % столбцы, опр-ют свободное пространство
A34t = A34;
A34t(h3, :) = 0;  A34t(h4, :) = 0;
A34t(:, t1) = 0;  A34t(:, t2) = 0;

k1 = 22;
figure(k1), imshow(A34t);  % Детектор 3, усеченный до 342 x 512


%ylim01 = [0.4 1];
xlim01 = [1 wid3]; % [1 512], wid3 вместо len3


A34h(1:dh, 1:wid3) = A34(h3:h4-1, 1:wid3); % A34(150:170-1, 1:512)
% size(A34h) = 20 512

for j = 1:wid3  % 1:342
   ma2(j) = mean(A34h(1:dh, j)); % Строка, средняя из 20-ти строк,  size(ma2) = 512
end


%x2 = 1:len3; 
x2 = 0.001:0.001:wid3/1000;  % /1000, чтобы коэф-ты полинома были намного больше 0
                             % не влияет на самый правый свободный член (коэф-т при степени 0)
p34 = polyfit(x2, ma2, 1);
r34p = polyval(p34, x2);     % прямая вдоль строки, средней из 20 строк, size(r34p) = 512

wid4 = wid3 - t2 + 1;

ma4(1:wid4) = ma2(t2:wid3);  % кусок справа средней (из 20 строк) строки


k1 = 220;
figure(k1), hold on
figure(k1), plot((t2:wid3), ma2(t2:wid3), 'b'); % среднее из верхних 20-ти строк
figure(k1), plot((t2:wid3), A34h(20, t2:wid3), 'r');  % size(A34h) = 20 512
figure(k1), title('');
figure(k1), hold off



x4 = 0.001:0.001:wid4/1000;
p04 = polyfit(x4, ma4, 1);
r04p = polyval(p04, x4);     % прямая средней (из 20 строк) строки


a50 = A34(h3, 1:wid3);       % произвольная строка h3 только для графика (через Pb)
a50v(1:wid4) = a50(t2:wid3); % только светлая часть строки

p50v = polyfit(x4, a50v, 1);
r50v = polyval(p50v, x4);    % прямая светлой части строки s1


k1 = 23;
figure(k1), hold on
figure(k1), plot((t2:wid3), ma2(t2:wid3), 'b'); % среднее из верхних 20-ти строк
figure(k1), plot((t2:wid3), r04p(1:wid4), 'r'); % прямая
figure(k1), plot((t2:wid3), a50v(1:wid4), 'g'); % светлый кусок строки 1:wid4
figure(k1), plot((t2:wid3), r50v(1:wid4), 'Color', [0.8 0.5 0]);  % прямая, аппрокс. светлого куска строки
figure(k1), hold off
%figure(k1), ylim(ylim01);
%figure(k1), xlim(xlim01);



for k = 1:h1
  A50(k, 1:wid3) = A34(k, 1:wid3); % все строки
  A50v(1:wid4) = A50(k, t2:wid3);  % только светлые части строк

  P50v = polyfit(x4, A50v, 2);
  R50v = polyval(P50v, x4);        % прямая светлой части одной строки 
  R50w(k, 1:wid4) = R50v(1:wid4);  % прямая светлых частей всех строк 
end

k1 = 24;
figure(k1), imshow(R50w); % прямые (аппроксимации) справа


r04q(1:h1) = r04p(1); % число - 1-й элемент среднего из 20-ти строк

k1 = 25;
figure(k1), hold on
figure(k1), plot(1:h1, r04q(1:h1), 'k'); % Прямая - среднее из 20-ти строк
figure(k1), plot(1:h1, R50w(1:h1, 1), 'r'); % первый элемент аппрокс. каждой строки
figure(k1), hold off
figure(k1), ylim(ylim01);


for k = 1:h1  % 1:512
  dRP(k) = r04p(1) ./ R50w(k, 1);
end

for k = 1:h1  % 1:512 
  RD1(k, 1:wid3) = A34(k, 1:wid3) .* dRP(k);  % Выровненный и по столбцам Detector 1, боковые 1:6 DM
end


CD1 = rot90(RD1, 3); % Поворот на 270 градусов CCW

k1 = 26;
figure(k1), imshow(CD1);  % Выровненный и по столбцам Detector 1, боковые 1:6 DM 


% imwrite(CD1, 'c1_d1u.bmp');

%A16 = uint16(round(CD1*65535));
%imwrite(A16, 'c1_d1u.tif');

%save('c1_d1u.mat', 'CD1');
% Concatenate arrays - c1u_all.m


