% 02.05.2026
%
% Pb
% a1_d1u.m
% Чтение файла 1.tif размером 512 x 4*704
% Извлечение Detector 1 - размером 512 x 704
% Оставлены боковые 1:6 DM из 1:11 DM
% Совмещение по яркости боковых 1:6 DM, остается 512 x 342
% 
% Выравнивание строк 
%
%



close all
clear all

A1 = imread('1.tif');
A2 = im2double(A1);

sza1 = size(A2);  % 512 x 4*704
h1 = sza1(1);     % 512

A3 = A2(1:h1, 0*704+1:1*704);  % Детектор 1

bok = 6;     % боковые, т.е. первые слева 1:6 DM
dm0 = 64; % Количество пикселей в DM, обычно 16*4 = 64
len0 = bok*dm0; % 6*64 = 384, Длина строки в пикселях

%for k = 1:h1
%  for j = 1:len0          % боковые 1:6 DM
%    A4(k, j) = A3(k, j);
%  end
%end
A4 = A3(1:h1, 1:len0); 

k1 = 2;
figure(k1), imshow(A4);  % первые 1:6 DM

%imwrite(A4, '5_4raw.jpg');




m1 = 2; % отсечь m1 пикселов с начала сенсора для боковых 1:6
n1 = 1; % отсечь n1 пикселов с конца сенсора для сенсоров 1:6

span = 5; % число пикселей при сглаживании по строкам,  z61a = smooth(z61, 5);  
% Для сравнения на сглаженном DM берутся точки, отстоящие на 2 пикселя от края, 
% т.к. span = 5, (span - 1)/2 = 2, 
sp = (span - 1)/2;  % sp = 2;

m2 = 24; % отсечь m2 пикселов с начала, лента транспортера 


if(0)
a4t = A4;
for t = 1:100:501;
  a4t(t, 1:len0) = 0;
end
k1 = 3;
figure(k1), imshow(a4t);  % Горизонтальные полоски через 100, чтобы опоределить h3, h4
end % if(0)


% Выделение области h3:h4 для совмещения DM вместо 1:h2
dh = 20;
h3 = 20;
h4 = h3 + dh;

hg = h3 + 10; % if(k==hg) plot()
gr1 = 0; % if(gr1) plot()    при вычислении e(1) - e(6)
ylim01 = [0.4 1];


a4h = A4;
a4h(h3, 1:len0) = 0;
a4h(h4, 1:len0) = 0;
k1 = 4;
figure(k1), imshow(a4h);  % Горизонтальные полоски h3, h4



% Усреднение для получения e(1) - e(6)

% h2 = 20; % столько верхних (первых) строк усредняется для получения e(1), если k = 1:h2

for k = h3:h4  % k = 1:h2  % 1:20
  
  % 1:6*64 = 384    % боковые, т.е. первые 1:6 DM  
  a5(1:len0) = A4(k, 1:len0); 
  %a5 = A4(k, 1:len0);  % то же
    
%  for i = 1:bok % 1:6
%    for j = 1:dm0 % 1:64
%      a6(j, i) = a5(j + (i-1)*dm0);
%    end
%  end  
  a6 = reshape(a5, 64, 6);
    
  % m1 = 2; % отсечь m1 пикселов с начала сенсора для боковых 1:6
  x5 = 1+m1 : dm0; % 1+m1 : 64;
  for i = 1:bok % 1:6   % 1:11
%    y5(i, x5-m1) = i;
    z5(i, x5-m1) = a6(x5, i); % A2(3:64, 1:11);
  end
  
  if(gr1)
  k1 = 5;
  figure(k1), plot(0,0); % чтобы обновить график
%  figure(k1), plot(x5-m1, z5(1, x5-m1));
  figure(k1), hold on
  for i = 1:bok  % 1:6 
    figure(k1), plot((i-1)*dm0 + x5-m1, z5(i, x5-m1));
  end
  figure(k1), hold off
  figure(k1), ylim([0 1]);
  end
  
  size5 = size(x5);
  sz5 = size5(2);  % 64 - m1 = 62
  dm1 = sz5;      % Длина в пикселях после отсечения m1 пикселей слева, 62

  % n1 = 1; % отсечь n1 пикселов с конца сенсора для сенсоров 1:6
  dm2 = dm1-n1;  % sz5-n1;    % Длина в пикселях после отсечения n1 пикселей справа, 61
  x6 = 1:dm2; % 1:61
  for i = 1:bok  % 1:6
%    y6(i, x6) = i;
    z6(i, x6) = z5(i, x6);
  end  
  
  if(gr1)
  k1 = 6;
  figure(k1), plot(0,0); % чтобы обновить график  
%  figure(k1), plot(x6, z6(1, x6));
  figure(k1), hold on
  for i = 1:bok  % 1:6 
    figure(k1), plot((i-1)*dm0 + x6, z6(i, x6));
  end
  figure(k1), hold off
  figure(k1), ylim(ylim01);
  end
  
  
  if(k==hg)
  % Только z6 на графике без пробелов:   for i = 1:6
  k1 = 9;
  figure(k1), plot(0,0); % чтобы обновить график
%  figure(k1), plot(x6, z6(1, x6));
  figure(k1), hold on
  for i = 1:bok  % 1:6 
    figure(k1), plot((i-1)*dm2 + x6, z6(i, x6));  % plot((i-1)*61 + x6, z6(i, x6));
  end
  figure(k1), hold off
  figure(k1), ylim(ylim01);
  end


for i = 1:6
  z60 = z6(i, x6);
  z60a = smooth(z60, span);
  z60b = z60a';
  z60c(i, x6) = z60b(x6);
end


if(gr1)
k1 = 100;
  figure(k1), plot(0,0); % чтобы обновить график
for i = 1:6
  figure(k1), hold on
  figure(k1), plot(x6 + (i-1)*dm2, z6(i, x6), '.', 'Color', 'r'); % DM 1
  figure(k1), plot(x6 + (i-1)*dm2, z60c(i, x6), 'b'); % сглаженный DM 1
  figure(k1), hold off
end
  figure(k1), ylim(ylim01);
end  % if(gr1)




% Коррекция строки 
% Совмещение DM относительно DM z62
% Совмещение DM т.о. чтобы z72b(61 - 2) == z73b(1 + 2),
% где z62b = smooth(z62, 5), z63b = smooth(z63, 5)

 
% Совмещение DM относ. z60c(2, :), т.е. относ. DM 2

d12 = z60c(1, dm2-sp) / z60c(2, 1+sp); 
d23 = z60c(2, dm2-sp) / z60c(3, 1+sp);
d34 = z60c(3, dm2-sp) / z60c(4, 1+sp);
d45 = z60c(4, dm2-sp) / z60c(5, 1+sp);
d56 = z60c(5, dm2-sp) / z60c(6, 1+sp);


% DM 1 
%d1 = z62b(1+sp)/z61b(dm2-sp); % dm2 = 61, dm2-sp = 59
%d1 = 1/d12;
D(1, k) = 1/d12; % D(1, k) Массиву D присваивается размер 1:h4 вместо h3:h4
if(k == h4)    % if(k == h2)
  e(1) = mean(D(1, h3:h4));  % e(1) = mean(D(1, 1:h2));  
end

% DM 2
%d2 = 1;   % Совмещение DM относительно z62b, поэтому d2 = 1 
%d2 = 1;   
D(2, k) = 1;
if(k == h4)  
  e(2) = 1;
end

% DM 3
%d3 = z62b(dm2-sp)/z63b(1+sp);  % sp = (span-1)/2 = 2;
%d3 = d23;
D(3, k) = d23;
if(k == h4)  
  e(3) = mean(D(3, h3:h4));
end

% DM 4
%d4 = d3 * z63b(dm2-sp) / z64b(1+sp);
%d4 = d23 * d34;
D(4, k) = d23 * d34;
if(k == h4)
  e(4) = mean(D(4, h3:h4));
end

% DM 5
%d5 = d4 * z64b(dm2-sp) / z65b(1+sp);
%d5 = d23 * d34 * d45;
D(5, k) = d23 * d34 * d45;
if(k == h4)
  e(5) = mean(D(5, h3:h4));
end

% DM 6
%d6 = d5 * z65b(dm2-sp) / z66b(1+sp);
%d6 = d23 * d34 * d45 * d56;
D(6, k) = d23 * d34 * d45 * d56;
if(k == h4) 
  e(6) = mean(D(6, h3:h4));
end


end % for k = h3:h4   % for k = 1:h2











gr2 = 1;  % Выводить или нет графики при создании массива строк

%h1 = 10;  % 256  % 512

for k = 1:h1

% Снова все сначала как для 1:h2

  a5(1:len0) = A4(k, 1:len0);
     
  %for i = 1:bok % 1:6
  %  for j = 1:dm0 % 1:64
  %    a6(j, i) = a5(j + (i-1)*dm0);
  %  end
  %end  
  a6 = reshape(a5, 64, 6);

  % m1 = 2; % отсечь m1 пикселов с начала сенсора для боковых 1:6
  x5 = 1+m1 : dm0; % 1+m1 : 64;
  for i = 1:bok % 1:6   % 1:11
    z5(i, x5-m1) = a6(x5, i); % A2(3:64, 1:11);
  end

  size5 = size(x5);
  sz5 = size5(2);  % 64 - m1 = 62
  dm1 = sz5;      % Длина в пикселях после отсечения m1 пикселей слева, 62

  % n1 = 1; % отсечь n1 пикселов с конца сенсора для сенсоров 1:6
  dm2 = dm1-n1;  % sz5-n1;    % Длина в пикселях после отсечения n1 пикселей справа, 61
  x6 = 1:dm2; % 1:61
  for i = 1:bok  % 1:6
    z6(i, x6) = z5(i, x6);
  end   
  

  for i = 1:6
    z60 = z6(i, x6);
    z60a = smooth(z60, span);
    z60b = z60a';
    z60c(i, x6) = z60b(x6);
  end  


  for i = 1:6
    z70(i, :)  = z6(i, :)   * e(i);
    z70b(i, :) = z60c(i, :) * e(i);
  end
  
  
if(gr2 && (k==hg))
k1 = 110;
  figure(k1), plot(0,0); % чтобы обновить график
figure(k1), hold on
for i = 1:6
  figure(k1), plot(x6 + (i-1)*dm2, z70(i, x6), '.', 'Color', 'r'); % DM 1
  figure(k1), plot(x6 + (i-1)*dm2, z70b(i, x6), 'b'); % сглаженный DM 1
end
figure(k1), hold off
figure(k1), ylim(ylim01);
end

row2 = cat(2, z70(1, :), z70(2, :), z70(3, :), z70(4, :), z70(5, :), z70(6, :));

len2 = bok*dm2;  % sz2 = bok*dm2;  % 6*61 = 366

row2a = row2;
for i = 1:len2  % 1:sz2
  if(row2a(i)<0) row2a(i) = 0; end
end

if(0) %if(gr2 && (k==hg))
k1 = 12;
figure(k1), plot(1:len2, row2a, '.', 'Color', 'r'); % 1:366
figure(k1), ylim(ylim01);  
end
  
% m2 = 24; % отсечь m2 пикселов с начала, лента транспортера 
len3 = len2 - m2;  % len3 = 366 - 24 = 342
for i = 1:len3  % 1:sz20   % 1:342
  r34(i) = row2a(m2+i);
end

r34s = smooth(r34, span);

%x2 = 1:len3;  % 1:sz20;
x2 = 0.001:0.001:len3/1000;  % /1000, чтобы коэф-ты полинома были намного больше 0
                             % не влияет на самый правый свободный член (коэф-т при степени 0)
p34 = polyfit(x2, r34, 2);
r34p = polyval(p34, x2);

R34(k, 1:len3) = r34(1:len3);
R34P(k, 1:len3) = r34p(1:len3);


end % for k = 1:h1


if(0)
% Изображение, чтобы показать границы между DM    
t = dm2-m2:dm2:len3; % Границы между DM сейачс в таких координатах, dm2 = 61, m2 = 24, len3 = 342
R34t = R34;
R34t(1:h1, t) = 0; % h1 = 256
k1 = 13;
figure(k1), imshow(R34t);  % Границы между DM обозначены
end


k1 = 14;
figure(k1), imshow(R34);  % С совмещенными DM

% imwrite(R34, 'a3_d1c.bmp');








% Выравнивание строк 

% из tif7_det4p_2.m

A34 = R34; % A2 в tif7_det4p_2.m

s1 = 330; % № строки для графика 22.

t1 = 31; t2 = 192; % t2 = 161; % столбцы, опр-ют свободное пространство
A34t = A34;
%A34t(s1, :) = 0;
%A34t(:, t1) = 0;  
A34t(:, t2) = 0;

k1 = 22;
figure(k1), imshow(A34t);  % Детектор 1, усеченный до 512 x 342


gr3 = 0; % Выводить или нет графики при создании массива строк

%ylim01 = [0.4 1];
xlim01 = [1 len3]; % [1 342]


% dh = 20; % столько строк усредняется

A34h(1:dh, 1:len3) = A34(h3:h4-1, 1:len3); % A34(30:50-1, 1:342)

%for j = 1:len3  % 1:342
%   ma2(j) = mean(A34h(1:dh, j)); % Строка, средняя из 20-ти строк,  size(ma2) = 342
%end


for j = 1:len3  % 1:342
    ma1 = 0;
  for i = 1:dh  
    ma1 = ma1 + A34h(i, j);  
  end
    ma2(j) = ma1/dh;  % Строка, средняя из 20-ти строк,  size(ma2) = 342  
end
% Получилось то же, что и   mean(A34h(1:dh, j)); 



%x2 = 1:len3; 
x2 = 0.001:0.001:len3/1000;  % /1000, чтобы коэф-ты полинома были намного больше 0
                             % не влияет на самый правый свободный член (коэф-т при степени 0)
p34 = polyfit(x2, ma2, 2);
r34p = polyval(p34, x2);     % парабола вдоль строки, средней из 20 строк, size(r34p) = 342

len4 = len3 - t2 + 1;

ma4(1:len4) = ma2(t2:len3);  % кусок справа средней (из 20 строк) строки


x4 = 0.001:0.001:len4/1000;
p04 = polyfit(x4, ma4, 2);
r04p = polyval(p04, x4);     % парабола средней (из 20 строк) строки


a50 = A34(s1, 1:len3);       % произвольная строка s1 только для графика (через Pb)
a50v(1:len4) = a50(t2:len3); % только светлая часть строки

p50v = polyfit(x4, a50v, 2);
r50v = polyval(p50v, x4);    % парабола светлой части строки s1


k1 = 23;
%figure(k1), plot(a2(1,:)-0.1, '.r');
figure(k1), hold on
%figure(k1), plot(ma2-0.1, 'b');  % вся базовая строка 1:342
%figure(k1), plot(r34p-0.1, 'r'); % аппрокс. всей базовой строки 1:342
figure(k1), plot((t2:len3), ma2(t2:len3), 'b'); % среднее из верхних 20-ти строк
figure(k1), plot((t2:len3), r04p(1:len4), 'r'); % парабола
%figure(k1), plot(a50 - 0.1, 'b');   % вся строка 1:342, проходящая через Pb
figure(k1), plot((t2:len3), a50v(1:len4), 'g'); % светлый кусок строки 1:192, проходящей через Pb
figure(k1), plot((t2:len3), r50v(1:len4), 'Color', [0.8 0.5 0]);  % аппрокс. светлого куска строки
figure(k1), hold off
figure(k1), ylim(ylim01);
figure(k1), xlim(xlim01);


for k = 1:h1
  A50(k, 1:len3) = A34(k, 1:len3); % все строки
  A50v(1:len4) = A50(k, t2:len3);  % только светлые части строк

  P50v = polyfit(x4, A50v, 2);
  R50v = polyval(P50v, x4);        % парабола светлой части одной строки 
  R50w(k, 1:len4) = R50v(1:len4);  % параболы светлых частей всех строк 
end

k1 = 24;
figure(k1), imshow(R50w); % параболы (аппроксимации) справа

r04q(1:h1) = r04p(1); % число - 1-й элемент среднего из 20-ти строк

k1 = 25;
figure(k1), hold on
figure(k1), plot(1:h1, r04q(1:h1), 'k'); % Прямая - среднее из 20-ти строк
figure(k1), plot(1:h1, R50w(1:h1, 1), 'r'); % первый элемент параболы (аппроксимации) каждой строки
figure(k1), hold off
figure(k1), ylim(ylim01);


for k = 1:h1  % 1:512
  dRP(k) = r04p(1) ./ R50w(k, 1);
end

for k = 1:h1  % 1:512 
  RD1(k, 1:len3) = A34(k, 1:len3) .* dRP(k);  % Выровненный Detector 1, слева 1:6
end

k1 = 26;
figure(k1), imshow(RD1);  % Выровненный Detector 1, слева 1:6 


% imwrite(RD1, 'a1_d1u.bmp');

%A16 = uint16(round(RD1*65535));
%imwrite(A16, 'a1_d1u.tif');

%save('a1_d1u.mat', 'RD1');
% Concatenate arrays - a1u_all.m



if(0)
% Среднее из верхних 20-ти строк - такое же, как светлый кусок строки ?
% Это кажется из-за вертикальных темных строк.
k1 = 30;
figure(k1), hold on
figure(k1), plot((t2:len3), ma2(t2:len3), 'b'); % среднее из верхних 20-ти строк
figure(k1), plot((t2:len3), A34(s1+1, t2:len3), 'g'); % светлый кусок строки 1:192, проходящей через Pb
figure(k1), hold off
end



