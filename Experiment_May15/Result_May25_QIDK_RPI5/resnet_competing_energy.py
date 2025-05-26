import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 创建保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# ResNet50 energy 数据
lambda_resnet = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 57,60,65,70]
resnet_rpi5_energy = [14.971104,15.838416,17.586932,19.406907,21.701736,25.554564,31.886556,37.39482,125.561,313.31524013,575.58683299,587.89381572,572.21954244,606.44470689,544.97112624]
resnet_qidk_energy = [16.683863,19.778712,24.936461,27.39144,33.391944,39.373452,48.458278,55.231776,137.95218,245.3135288,581.70698136,727.7946426,740.67839325,743.71563861,727.00080831]


# 自定义偏移（你可以改这些来控制标注位置）
# 设置每个点的标注偏移（单位为 points），分别为 (x, y)
offsets_qidk = [(0, 15), (0, 15), (0, 15), (0, 15), (0, 15), (0, 15),
                (0, 15), (-7, 15), (-14, 15), (15, -20), (-15, 15), (-20, 7), (0,10),(0,10),(0,10)]
offsets_rpi5 = [(0, -15), (0, -15), (0, -15), (0, -15), (0, -15), (0, -15),
                (0, -15), (0, -15), (15, -15), (-15, 15), (-30, -15), (0, -25), (0,10),(0,10),(0,10)]
# 设置字体
plt.rcParams.update({'font.size': 16})

# 绘图
plt.figure(figsize=(12, 6))

# 找到 λ = 57 的索引位置
split_index = lambda_resnet.index(57)

# 前半段（实线）
plt.plot(lambda_resnet[:split_index+1], resnet_rpi5_energy[:split_index+1],
         marker='o', color='red', linestyle='-', label='RPI5')
plt.plot(lambda_resnet[:split_index+1], resnet_qidk_energy[:split_index+1],
         marker='s', color='blue', linestyle='-', label='QIDK')

# 后半段（虚线）
plt.plot(lambda_resnet[split_index:], resnet_rpi5_energy[split_index:],
         marker='o', color='red', linestyle='--')
plt.plot(lambda_resnet[split_index:], resnet_qidk_energy[split_index:],
         marker='s', color='blue', linestyle='--')

# 标注每个点（偏移可自定义）
# 添加标注
for i, x in enumerate(lambda_resnet):
    offset_x_rpi5, offset_y_rpi5 = offsets_rpi5[i]
    offset_x_qidk, offset_y_qidk = offsets_qidk[i]

    trans_rpi5 = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_rpi5, y=offset_y_rpi5, units='points')
    trans_qidk = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_qidk, y=offset_y_qidk, units='points')

    plt.text(x, resnet_rpi5_energy[i], f"{resnet_rpi5_energy[i]:.2f}", ha='center',
             fontsize=12, transform=trans_rpi5)
    plt.text(x, resnet_qidk_energy[i], f"{resnet_qidk_energy[i]:.2f}", ha='center',
             fontsize=12, transform=trans_qidk)
    
# λ = 40 的垂直线
plt.axvline(x=45, color='gray', linestyle='--')
plt.text(49.5, 450, 'Breakpoint: λ = 45', fontsize=12, va='center', ha='right', color='gray')

# 插入这里
plt.axvline(x=57, color='black', linestyle=':', linewidth=1)

# 设置 x 轴刻度：在默认 range 里手动加上 57
xticks = list(range(0, 80, 5))
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

plt.xlim(0, 75)

# y轴范围：自动扩展上下各 15%
all_vals = resnet_rpi5_energy + resnet_qidk_energy
y_min, y_max = min(all_vals), max(all_vals)
margin = (y_max - y_min) * 0.1
plt.ylim(y_min - margin, y_max + margin)

# 标签与样式
plt.xlabel("λ", fontsize=16)
plt.ylabel("Energy per image (mJ)", fontsize=16)
plt.legend()
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

# 保存图像
plt.savefig(os.path.join(save_dir, "resnet50_competing_energy.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "resnet50_competing_energy.pdf"), bbox_inches='tight')
plt.close()
