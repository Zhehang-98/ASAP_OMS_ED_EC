import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 创建保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# 数据
lambda_vals = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 57,60,65,70]
rpi5_power = [0.415864,0.439956,0.462814,0.497613,0.516708,0.555534,
0.613203,0.623247,1.25561,2.824441,4.370771,4.344471,
4.216177,4.344471,3.775084]
qidk_power = [0.340487,0.429972,0.530563,0.570655,0.654744,0.729138,
0.794398,0.812232,1.277335,2.57899,5.497656,6.24931,
6.037975,5.912359,5.684579]





# 自定义偏移（你可以改这些来控制标注位置）
offsets_rpi5 = [(0, 15), (0, 15), (0, -15), (0, -15), (0, -15), (0, -15),
                (0, -15), (0, -15), (15, -15), (-15, 20), (0, 10), (3, -15), (0,10),(0,10),(0,10)]
offsets_qidk = [(0, -15), (0, -15), (0, 15), (0, 15), (0, 15), (0, 15),
                (0, 15), (0, 15), (-15, 15), (15, -15), (-5, 15), (-10, 10), (0,5),(0,5),(0,5)]

# 字体
plt.rcParams.update({'font.size': 16})

# 画图
plt.figure(figsize=(12, 6))
# 找到 λ = 57 的索引位置
split_index = lambda_vals.index(57)

# 前半段（实线）
plt.plot(lambda_vals[:split_index+1], rpi5_power[:split_index+1],
         marker='o', color='red', linestyle='-', label='RPI5')
plt.plot(lambda_vals[:split_index+1], qidk_power[:split_index+1],
         marker='s', color='blue', linestyle='-', label='QIDK')

# 后半段（虚线）
plt.plot(lambda_vals[split_index:], rpi5_power[split_index:],
         marker='o', color='red', linestyle='--')
plt.plot(lambda_vals[split_index:], qidk_power[split_index:],
         marker='s', color='blue', linestyle='--')

# 标注每个点（偏移可自定义）
# 添加标注
for i, x in enumerate(lambda_vals):
    offset_x_rpi5, offset_y_rpi5 = offsets_rpi5[i]
    offset_x_qidk, offset_y_qidk = offsets_qidk[i]

    trans_rpi5 = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_rpi5, y=offset_y_rpi5, units='points')
    trans_qidk = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_qidk, y=offset_y_qidk, units='points')

    plt.text(x, rpi5_power[i], f"{rpi5_power[i]:.2f}", ha='center',
             fontsize=12, transform=trans_rpi5)
    plt.text(x, qidk_power[i], f"{qidk_power[i]:.2f}", ha='center',
             fontsize=12, transform=trans_qidk)

# λ = 40 的垂直线
plt.axvline(x=45, color='gray', linestyle='--')
plt.text(49.9, 5, 'Breakpoint: λ = 45', fontsize=12, va='center', ha='right', color='gray')

# 插入这里
plt.axvline(x=57, color='black', linestyle=':', linewidth=1)

# 坐标轴
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

# y轴上下加 margin
y_all = rpi5_power + qidk_power
y_min, y_max = min(y_all), max(y_all)
margin = (y_max - y_min) * 0.1
plt.ylim(y_min - margin, y_max + margin)

# 标签
plt.xlabel("λ", fontsize=16)
plt.ylabel("Power Consumption (W)", fontsize=16)
plt.legend()
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

# 保存图像
plt.savefig(os.path.join(save_dir, "resnet50_power_comparison.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "resnet50_power_comparison.pdf"), bbox_inches='tight')
plt.close()
