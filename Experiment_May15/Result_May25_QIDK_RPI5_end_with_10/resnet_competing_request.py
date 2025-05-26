import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 创建保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# ResNet50 throughput 数据
lambda_resnet = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 57]
resnet_rpi5_ec = [518,1010,1488,2013,2499,2949,
3518,3987,4539,4708,4792,4805]
resnet_rpi5_ed = [0,0,0,0,0,0,0,0,51,218,626,705]
resnet_qidk_ec = [500,1000,1526,1997,2560,3041,
3476,3934,4477,4705,4807,4798]
resnet_qidk_ed = [0,0,0,0,0,0,0,0,52,225,622,788]





# 单位转换：images per second
resnet_rpi5_ec_ips = [x / 100.0 for x in resnet_rpi5_ec]
resnet_rpi5_ed_ips = [x / 100.0 for x in resnet_rpi5_ed]
resnet_qidk_ec_ips = [x / 100.0 for x in resnet_qidk_ec]
resnet_qidk_ed_ips = [x / 100.0 for x in resnet_qidk_ed]

# 设置字体
plt.rcParams.update({'font.size': 16})

# 自定义偏移（你可以在这里修改以微调每个点的标注）

offsets_rpi5_ec = [(-10, 8),   (-10, 8),  (15, -14),   (-10, 8) ,  (15, -14) , (15, -14),
                (-10, 8),  (-10, 8),  (-10, 8), (0, 10) , (-4, -15), (10, 10)]
offsets_qidk_ec = [(15, -12),  (15, -12), (-10, 8), (15, -14),   (-10, 8),  (-10, 8),
                (15, -14), (15, -14), (15, -14), (0, -15),  (-4, 10), (10, -15)]
offsets_rpi5_ed = [(-15, 7),   (0, 7),     (0, 7),     (0, 7),     (0, 7),     (0, 7),
                (0, 7), (0, -15), (3, -15),  (0, -15),  (-7, 8), (14, -20)]
offsets_qidk_ed = [(0, -15),   (0, -15),   (0, -15), (0, -15), (0, -15), (0, -15),
                (0, -15), (0, 7), (3, 7),  (0, 10), (-3, -20),  (-14, 15)]

# 绘图
plt.figure(figsize=(12, 6))

split_index = lambda_resnet.index(57)

# 前半段（实线）
plt.plot(lambda_resnet[:split_index+1], resnet_rpi5_ec_ips[:split_index+1],
         marker='o', color='red', linestyle='-', label='RPI5 EC')
plt.plot(lambda_resnet[:split_index+1], resnet_qidk_ec_ips[:split_index+1],
         marker='s', color='blue', linestyle='-', label='QIDK EC')

plt.plot(lambda_resnet[:split_index+1], resnet_rpi5_ed_ips[:split_index+1],
         marker='o', color='darkgreen', linestyle='-', label='RPI5 ED', alpha=0.8)
plt.plot(lambda_resnet[:split_index+1], resnet_qidk_ed_ips[:split_index+1],
         marker='s', color='indigo', linestyle='-', label='QIDK ED', alpha=0.6)


# 标注每个点（偏移可自定义）
# 添加标注
for i, x in enumerate(lambda_resnet):
    offset_x_rpi5, offset_y_rpi5 = offsets_rpi5_ec[i]
    offset_x_qidk, offset_y_qidk = offsets_qidk_ec[i]

    trans_rpi5 = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_rpi5, y=offset_y_rpi5, units='points')
    trans_qidk = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_qidk, y=offset_y_qidk, units='points')

    plt.text(x, resnet_rpi5_ec_ips[i], f"{resnet_rpi5_ec_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_rpi5)
    plt.text(x, resnet_qidk_ec_ips[i], f"{resnet_qidk_ec_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_qidk)
    
for i, x in enumerate(lambda_resnet):
    offset_x_rpi5, offset_y_rpi5 = offsets_rpi5_ed[i]
    offset_x_qidk, offset_y_qidk = offsets_qidk_ed[i]

    trans_rpi5 = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_rpi5, y=offset_y_rpi5, units='points')
    trans_qidk = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_qidk, y=offset_y_qidk, units='points')

    plt.text(x, resnet_rpi5_ed_ips[i], f"{resnet_rpi5_ed_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_rpi5)
    plt.text(x, resnet_qidk_ed_ips[i], f"{resnet_qidk_ed_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_qidk)


plt.axvline(x=45, color='gray', linestyle='--')
plt.text(48.7, 14, 'Breakpoint: λ = 45', fontsize=12, va='center', ha='right', color='gray')

# 插入这里
plt.axvline(x=57, color='black', linestyle=':', linewidth=1)
# 坐标轴
xticks = list(range(0, 60, 5))
if 57 not in xticks:
    xticks.append(57)
    xticks.sort()

# 设置 tick label 和颜色
xtick_labels = [str(x) for x in xticks]
xtick_colors = ['black' if x != 57 else 'darkorange' for x in xticks]  # 标出 λ=57 是蓝色

# 应用刻度和颜色
plt.xticks(xticks, labels=xtick_labels)
ax = plt.gca()
for ticklabel, color in zip(ax.get_xticklabels(), xtick_colors):
    ticklabel.set_color(color)
# 设置坐标轴

plt.xlim(0, 60)


# y轴范围（上下扩展 15%）
all_vals = resnet_rpi5_ec_ips + resnet_rpi5_ed_ips + resnet_qidk_ec_ips + resnet_qidk_ed_ips
y_min, y_max = min(all_vals), max(all_vals)
margin = (y_max - y_min) * 0.1
plt.ylim(y_min - margin, y_max + margin)

# 标签与样式
plt.xlabel("λ", fontsize=16)
plt.ylabel("Requests per second", fontsize=16)
plt.legend()
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

# 保存图像
plt.savefig(os.path.join(save_dir, "resnet50_competing_requests.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "resnet50_competing_requests.pdf"), bbox_inches='tight')
plt.close()
