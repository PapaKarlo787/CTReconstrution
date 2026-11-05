% 02.05.2026
%
% Concatenate arrays
%
% Pb
% c1_d4u.m --> A40
% c1_d2u.m --> A20
% c1_d1u.m --> A10
% c1_d3u.m --> A30
%
% A = cat(2, A10, A20, A30, A40);
% A16 = uint16(round(A*65535));
% imwrite(A16, 'c1.tif');
%



close all
clear all


% Detector 1

A1 = load('c1_d1u.mat'); % 512 x 342
A10 = A1.CD1;

k1 = 3;
figure(k1), imshow(A10);
figure(k1), title('Detector 1');




clear A1 A2

% Detector 2

A1 = load('c1_d2u.mat');  % 512 x 342
A20 = A1.CD1;

k1 = 6;
figure(k1), imshow(A20);
figure(k1), title('Detector 2');




clear A1 A2

% Detector 3

A1 = load('c1_d3u.mat');  % 512 x 342
A30 = A1.CD1;

k1 = 9;
figure(k1), imshow(A30);
figure(k1), title('Detector 3');




clear A1 A2

% Detector 4

A1 = load('c1_d4u.mat');  % 512 x 342
A40 = A1.CD1;

k1 = 12;
figure(k1), imshow(A40);
figure(k1), title('Detector 4');




A = cat(2, A10, A20, A30, A40);  % 512 x 4*342

k1 = 13;
figure(k1), imshow(A);

%A16 = uint16(round(A*65535));
%imwrite(A16, 'c1.tif');



