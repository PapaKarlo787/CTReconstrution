% 01.05.2026
%
% plot_c3_det1u.m
%
% Чтение ('Cu_rect_c3_det1u.txt') из rect_c3_det1u.m 
% Чтение ('Au_rect_c3_det1u.txt') из rect_c3_det1u.m 
% (Cu, Au, 2026_04_22, Detector1: 140 kV, low)
%
% Ослабление в Cu, Au
%
% Сравнение с теорией
% Чтение файла Cu_03.txt (mu_Cu.m)
% Чтение файла Au_03.txt (mu_Au.m)
%
% Cu: эксп. данные НЕ совпадают с теорией
% Eef = 90 keV для теор. Cu
% Au: эксп. данные НЕ совпадают с теорией, слишком темные прямоугольники
% Eef = 125 keV для теор. Au
%
%
% 02.05.2026
%
% plot_c3_d1u.m 
%
% Чтение ('Al_rect_c3_d1u.txt') из rect_c3_d1u.m 
%
% Ослабление в Al
%
% Сравнение с теорией
% Чтение файла Al_03.txt (mu_Al.m)
%
%
% 02.05.2026
%
% plot_c1_d4u.m 
%
% Чтение ('Pb_rect_c1_d4u.txt') из rect_c1_d4u.m 
%
% Ослабление в Pb
%
% Сравнение с теорией
% Чтение файла Pb_03.txt (mu_Pb.m)
%
% 11.05.2026
% plot_c1_d4v.m  (det4: 200 kV, high)
% Чтение файла Pb_rect_c1_d4v.txt
% Значение Фона и Средние величины из 5-ти Pb прямоугольников.
% Для вычисления теоретических эфф. энергий берется спектр излучения, прошедшего через 1 мм Cu
% Вычисление эфф. энергии и запись файлов:
% Pb_Eef_c1_d4v.txt, Эксперимент.
% Pb_Et_c1_d4v.txt,  Теор.
%
%


close all
clear all



%ro_Al = 2.700;  % g/cm3
ro_Cu = 8.960;  % g/cm3   % для фильтра 1 мм Cu
%ro_Ag = 10.50;  % g/cm3
ro_Pb = 11.35;  % g/cm3
%ro_Au = 19.32;  % g/cm3


dE = 1e-6;
%E03 = 1e-3:dE:1;  % от 1 кэВ до 1 МэВ  % шаг 1 эВ, size(E03) = 999001
%lnE03 = log(E03);


A1 = load('c1_d4u.mat');
A6 = A1.CD1; 

sza1 = size(A6);  % 512 x 342
h1   = sza1(1);
len3 = sza1(2);

k1 = 1;
figure(k1), imshow(A6);
figure(k1), title('Pb c1-d4u.m 2000kV, high');


% Чтение файла (mu_Cu.m)   % для фильтра 1 мм Cu
fileID = fopen('Cu_03.txt', 'r');
Cu_03 = fscanf(fileID, '%f %f', [2, inf]);
fclose(fileID);
%E03 = Cu_03(1, :);
Mu_mo_Cu03 = Cu_03(2, :);


% Теория
% Чтение файла (mu_Pb.m)
fileID = fopen('Pb_03.txt', 'r');
Pb_03 = fscanf(fileID, '%f %f', [2, inf]);
fclose(fileID);

E03 = Pb_03(1, :);
Mu_mo_Pb03 =  Pb_03(2, :);

Em = 0.2; % МэВ
I0 = Em - E03;
for(j = 1:length(I0))
  if(I0(j) < 0)
    I0(j) = 0;
  end
end

% Прямая (в semilogy)
d = 0:0.01:0.2;  %  см Pb
%    E03(89000) = 90 keV
%    E03(99000) = 100 keV
%    E03(109000) = 110 keV
Ime = 0.6.*exp(-Mu_mo_Pb03(77000)*ro_Pb*d); % Eef = 78 keV  % Experiment 'r'

Imt = 0.6.*exp(-Mu_mo_Pb03(73000)*ro_Pb*d); % Eef = 74 keV   % Theory 'b'


% Эксперимент 1 (IMG_1_2.jpg)

% Pb, Чтение файла
fileID = fopen('Pb_rect_c1_d4v.txt', 'r');
Pb_04 = fscanf(fileID, '%f %f', [2 inf]);
fclose(fileID);
d6 = Pb_04(1, :);
mA6 = Pb_04(2, :);


% На детектор high поступает излучение со спектром, прошедшим 
% через лист меди толщиной 1 мм.
% Теоретически, это IC = I0.*exp(-Mu_mo_Cu03*ro_Cu*0.1);
IC = I0.*exp(-Mu_mo_Cu03*ro_Cu*0.1);    % 0.1 см Cu

% Теоретически для испытанных толщин Pb
I1 = IC.*exp(-Mu_mo_Pb03*ro_Pb*d6(1));  % 0
I2 = IC.*exp(-Mu_mo_Pb03*ro_Pb*d6(2));  % 0.01 см Pb
I3 = IC.*exp(-Mu_mo_Pb03*ro_Pb*d6(3));  % 0.02 см Pb
I4 = IC.*exp(-Mu_mo_Pb03*ro_Pb*d6(4));  % 0.03 см Pb
I5 = IC.*exp(-Mu_mo_Pb03*ro_Pb*d6(5));  % 0.05 см Pb
I6 = IC.*exp(-Mu_mo_Pb03*ro_Pb*d6(6));  % 0.10 см Pb

% Теоретически
trapzI(1) = trapz(I1)*dE;
trapzI(2) = trapz(I2)*dE;
trapzI(3) = trapz(I3)*dE;
trapzI(4) = trapz(I4)*dE;
trapzI(5) = trapz(I5)*dE;
trapzI(6) = trapz(I6)*dE;

tc = mA6(1)/trapzI(1); % coefficient

tI = tc*trapzI; % 54



k1 = 14;
figure(k1), semilogy(d6, mA6, 'or'); % Эксперим.
figure(k1), hold on
%figure(k1), semilogy(d, Ime, 'r');   % Эксперим.
figure(k1), semilogy(d6, tI, 'ob'); % Теор.
%figure(k1), semilogy(d, Imt, 'b');  % Теор.
figure(k1), hold off
figure(k1), title('Pb, det4 (200kV, high)', 'FontWeight', 'Bold');
figure(k1), ylim([0.001 1]);
figure(k1), xlim([0 0.11]);
figure(k1), xlabel('d, cm', 'FontWeight', 'Bold');
figure(k1), ylabel('Intensity', 'FontWeight', 'Bold');
%figure(k1), legend('exper.', '78keV', 'theory', '74keV' );
figure(k1), legend('exper.', 'theory');




% Experimental data

dx = 0.0001; % для графиков

% mA6(1) == Background

%x1 = 0:0.0001:d6(1);
%Muro(1) = log(mA6(1)/mA6(1))/d6(1);  log(1)/0;
%Y1 = mA6(1)*exp(-Muro(1)*x1);   % 0 см
x1 = 0;
Muro(1) = 0; % на самом деле, ближе к бесконечности
Y1 = mA6(1);

x2 = 0:dx:d6(2);
Muro(2) = log(mA6(1)/mA6(2))/d6(2);
Y2 = mA6(1)*exp(-Muro(2)*x2);   % 0.005 см Cu

x3 = 0:dx:d6(3);
Muro(3) = log(mA6(1)/mA6(3))/d6(3);
Y3 = mA6(1)*exp(-Muro(3)*x3);   % 0.01 см Cu

x4 = 0:dx:d6(4);
Muro(4) = log(mA6(1)/mA6(4))/d6(4);
Y4 = mA6(1)*exp(-Muro(4)*x4);   % 0.05 см Cu

x5 = 0:dx:d6(5);
Muro(5) = log(mA6(1)/mA6(5))/d6(5);
Y5 = mA6(1)*exp(-Muro(5)*x5);   % 0.1 см Cu

x6 = 0:dx:d6(6);
Muro(6) = log(mA6(1)/mA6(6))/d6(6);
Y6 = mA6(1)*exp(-Muro(6)*x6);   % 0.15 см Cu


k1 = 16;
figure(k1), semilogy(d6, mA6, 'or'); % Эксперим.
figure(k1), hold on
%figure(k1), semilogy(0, Background, 'or'); % Эксперим. Background
%figure(k1), semilogy(x1, Y1, 'r'); % x1==0
figure(k1), semilogy(x2, Y2, 'r');
figure(k1), semilogy(x3, Y3, 'r');
figure(k1), semilogy(x4, Y4, 'r');
figure(k1), semilogy(x5, Y5, 'r');
figure(k1), semilogy(x6, Y6, 'r');
figure(k1), hold off
figure(k1), title('Pb, det4 (200kV, high), Experiment', 'FontWeight', 'Bold');
figure(k1), ylim([0.001 1]);
figure(k1), xlim([0 0.11]);
figure(k1), xlabel('d, cm', 'FontWeight', 'Bold');
figure(k1), ylabel('Intensity', 'FontWeight', 'Bold');


for j = 1:6
  i1 = 0;
  for i = 1 : 999000
    if( (Mu_mo_Pb03(i) < Muro(j)/ro_Pb) && (i1==0) )
      Nef(j) = i;
      i1 = 1;
    end
  end
end

Eef(1) = 0;
for j = 2:6
  Eef(j) = 1e6*E03(Nef(j)); % эВ
end

for j = 1:6
  Eef1(j) = round(Eef(j)); % для записи в файл %d
end

% Pb, Запись в файл
if(0)
Pb_07(1, :) = d6(:);
Pb_07(2, :) = mA6(:);
Pb_07(3, :) = Muro(:);
Pb_07(4, :) = Eef1(:);
fileID = fopen('Pb_Eef_c1_d4v.txt', 'w'); % c1_d4v
fprintf(fileID, '%f %f %f %d\n', Pb_07);
fclose(fileID);
end



% Theoretical data
% Murot - Muro theoretical
% Yt - Y theoretical
% Et - Eef theoretical

dx = 0.0001; % для графиков

% tI(1) == mA6(1) == Background

%x1 = 0:0.0001:d6(1);
%Muro(1) = log(mA6(1)/mA6(1))/d6(1);  log(1)/0;
%Y1 = mA6(1)*exp(-Muro(1)*x1);     % 0 см
%x1 = 0;
Murot(1) = 0; % на самом деле, ближе к бесконечности
Yt1 = tI(1);

%x2 = 0:dx:d6(2);
Murot(2) = log(tI(1)/tI(2))/d6(2);
Yt2 = tI(1)*exp(-Murot(2)*x2);     % 0.005 см Cu

%x3 = 0:dx:d6(3);
Murot(3) = log(tI(1)/tI(3))/d6(3);
Yt3 = tI(1)*exp(-Murot(3)*x3);     % 0.01 см Cu

%x4 = 0:dx:d6(4);
Murot(4) = log(tI(1)/tI(4))/d6(4);
Yt4 = tI(1)*exp(-Murot(4)*x4);     % 0.05 см Cu

%x5 = 0:dx:d6(5);
Murot(5) = log(tI(1)/tI(5))/d6(5);
Yt5 = tI(1)*exp(-Murot(5)*x5);     % 0.1 см Cu

%x6 = 0:dx:d6(6);
Murot(6) = log(tI(1)/tI(6))/d6(6);
Yt6 = tI(1)*exp(-Murot(6)*x6);     % 0.15 см Cu


k1 = 17;
figure(k1), semilogy(d6, tI, 'ob'); % Theory
figure(k1), hold on
%figure(k1), semilogy(x1, Yt1, 'b'); % x1==0
figure(k1), semilogy(x2, Yt2, 'b');
figure(k1), semilogy(x3, Yt3, 'b');
figure(k1), semilogy(x4, Yt4, 'b');
figure(k1), semilogy(x5, Yt5, 'b');
figure(k1), semilogy(x6, Yt6, 'b');
figure(k1), hold off
figure(k1), title('Pb, det4 (200kV, high), Theory', 'FontWeight', 'Bold');
figure(k1), ylim([0.001 1]);
figure(k1), xlim([0 0.11]);
figure(k1), xlabel('d, cm', 'FontWeight', 'Bold');
figure(k1), ylabel('Intensity', 'FontWeight', 'Bold');


for j = 1:6
  i1 = 0;
  for i = 1 : 999000
    if( (Mu_mo_Pb03(i) < Murot(j)/ro_Pb) && (i1==0) )
      Nt(j) = i;
      i1 = 1;
    end
  end
end

Et(1) = 0;
for j = 2:6
  Et(j) = 1e6*E03(Nt(j)); % эВ
end

for j = 1:6
  Et1(j) = round(Et(j)); % для записи в файл %d
end

% Pb, Запись в файл, Theory
if(0)
Pb_07(1, :) = d6(:);
Pb_07(2, :) = tI(:);
Pb_07(3, :) = Murot(:);
Pb_07(4, :) = Et1(:);
fileID = fopen('Pb_Et_c1_d4v.txt', 'w'); % c1_d4v
fprintf(fileID, '%f %f %f %d\n', Pb_07);
fclose(fileID);
end









