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
%


close all
clear all



%ro_Al = 2.700;  % g/cm3
%ro_Cu = 8.960;  % g/cm3
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
fileID = fopen('Pb_rect_c1_d4u.txt', 'r');
Pb_04 = fscanf(fileID, '%f %f', [2 inf]);
fclose(fileID);
d6 = Pb_04(1, :);
mA6 = Pb_04(2, :);


% Теоретически для испытанных толщин Pb
I1 = I0.*exp(-Mu_mo_Pb03*ro_Pb*d6(1));  % 0.01 см Pb
I2 = I0.*exp(-Mu_mo_Pb03*ro_Pb*d6(2));  % 0.02 см Pb
I3 = I0.*exp(-Mu_mo_Pb03*ro_Pb*d6(3));  % 0.03 см Pb
I4 = I0.*exp(-Mu_mo_Pb03*ro_Pb*d6(4));  % 0.05 см Pb
I5 = I0.*exp(-Mu_mo_Pb03*ro_Pb*d6(5));  % 0.10 см Pb
% Теоретически
trapzI(1) = trapz(I1)*dE;
trapzI(2) = trapz(I2)*dE;
trapzI(3) = trapz(I3)*dE;
trapzI(4) = trapz(I4)*dE;
trapzI(5) = trapz(I5)*dE;

tI = 54*trapzI;



k1 = 14;
figure(k1), semilogy(d6, mA6, 'or'); % Эксперим.
figure(k1), hold on
figure(k1), semilogy(d, Ime, 'r');   % Эксперим.
figure(k1), semilogy(d6, tI, 'ob'); % Теор.
figure(k1), semilogy(d, Imt, 'b');  % Теор.
figure(k1), hold off
figure(k1), title('Pb, det4 (200kV, high)', 'FontWeight', 'Bold');
figure(k1), ylim([0.001 1]);
figure(k1), xlim([0 0.11]);
figure(k1), xlabel('d, cm', 'FontWeight', 'Bold');
figure(k1), ylabel('Intensity', 'FontWeight', 'Bold');
figure(k1), legend('exper.', '78keV', 'theory', '74keV' );


