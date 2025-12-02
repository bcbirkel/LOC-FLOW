%plot location distribution in 3d
loc = './catalogSA_allday.txt'

a = load(loc);
lon = a(:,7);
lat = a(:,8);
dep = a(:,9);

scatter3(lon,lat,dep,'filled','b'), view(-60,60);
ylim([27.5,28.5]) %lat range
xlim([85.2,86]) %lon range
zlim([0,40]);   %dep range
grid on; alpha(0.45); box on;
set(gca,'zDir','reverse');
xlabel('Lon.');
ylabel('Lat.');
zlabel('Depth');
set(gca,'FontSize',20)
saveas(gca,'3Dlocation.pdf')
