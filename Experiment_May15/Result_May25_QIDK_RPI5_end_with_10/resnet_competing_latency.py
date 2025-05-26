import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 创建保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# ResNet50 latency 数据
lambda_resnet = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 57]

resnet_rpi5_latency = [36,36,38,39,42,46,52,60,100,148,264,459]
resnet_qidk_latency = [49,46,47,48,51,54,61,68,108,154,229,411]

# 设置每个点的标注偏移（单位为 points），分别为 (x, y)
offsets_rpi5 = [(0, -15), (0, -15), (0, -15), (0, -15), (0, -15), (0, -15),
                (0, -15), (0, -15), (13, -15), (5, -15), (-15, 10), (-10, 10)]
offsets_qidk = [(0, 10), (0, 10), (0, 10), (0, 10), (0, 10), (0, 10),
                (0, 10), (0, 10), (-13, 10), (-5, 10), (5, -15), (15, -15)]




# 设置字体
plt.rcParams.update({'font.size': 16})

# 绘图
plt.figure(figsize=(12, 6))
plt.plot(lambda_resnet, resnet_rpi5_latency, marker='o', color='red', label='RPI5')
plt.plot(lambda_resnet, resnet_qidk_latency, marker='s', color='blue', label='QIDK')

# 添加标注
for i, x in enumerate(lambda_resnet):
    offset_x_rpi5, offset_y_rpi5 = offsets_rpi5[i]
    offset_x_qidk, offset_y_qidk = offsets_qidk[i]

    trans_rpi5 = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_rpi5, y=offset_y_rpi5, units='points')
    trans_qidk = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_qidk, y=offset_y_qidk, units='points')

    plt.text(x, resnet_rpi5_latency[i], f"{resnet_rpi5_latency[i]}", ha='center',
             fontsize=12, transform=trans_rpi5)
    plt.text(x, resnet_qidk_latency[i], f"{resnet_qidk_latency[i]}", ha='center',
             fontsize=12, transform=trans_qidk)
    

# λ = 40 的垂直线
plt.axvline(x=45, color='gray', linestyle='--')
plt.text(48.7, 300, 'Breakpoint: λ = 45', fontsize=12, va='center', ha='right', color='gray')

# 插入这里
plt.axvline(x=57, color='black', linestyle=':', linewidth=1)

# 设置 x 轴刻度：在默认 range 里手动加上 57
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

# y轴上下扩展 15%
all_vals = resnet_rpi5_latency + resnet_qidk_latency
y_min, y_max = min(all_vals), max(all_vals)
margin = (y_max - y_min) * 0.1
plt.ylim(y_min - margin, y_max + margin)

# 标签与图例
plt.xlabel("λ", fontsize=16)
plt.ylabel("Avg Inference Time (ms)", fontsize=16)
plt.legend()
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

# 保存图像
plt.savefig(os.path.join(save_dir, "resnet50_competing_latency.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "resnet50_competing_latency.pdf"), bbox_inches='tight')
plt.close()
