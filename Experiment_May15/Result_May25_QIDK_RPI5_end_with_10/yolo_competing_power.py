import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 创建保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# 数据
lambda_vals = list(range(1, 11))

plt.figure(figsize=(12, 6))

rpi5_power = [0.496235,0.530405,0.537004,0.548001,0.544495,0.8266,
1.361104,1.939111,4.892131,4.070214]
qidk_power = [0.35838,0.343502,0.370996,0.456881,0.429936,0.671804,
1.06913,1.967308,5.383124,5.854677]






# 自定义偏移（你可以改这些来控制标注位置）
offsets_rpi5 = [(0, 15), (0, 15), (0, 15), (0, 15), (2, 15), (0, 15),
                (-5, 15), (15, -15), (15, 10), (5, 10)]
offsets_qidk = [(0, -15), (0, -15), (0, -15), (0, -15), (2, -15), (0, -15),
                (5, -15), (-15, 15), (0, 15), (0, 15), (0, 15)]


# 字体
plt.rcParams.update({'font.size': 16})

split_index = lambda_vals.index(10)

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
    

# λ = 6 的垂直线
plt.axvline(x=6, color='gray', linestyle='--')
plt.text(6.6, 4.5, 'Breakpoint: λ = 6', fontsize=12, va='center', ha='right', color='gray')

# 插入这里
plt.axvline(x=10, color='black', linestyle=':', linewidth=1)
# 坐标轴
plt.xticks(range(0, 11, 1))

# 单独把 x=10 的刻度变颜色
ax = plt.gca()
for label in ax.get_xticklabels():
    if label.get_text() == "10":
        label.set_color("darkorange")

plt.xlim(0, 11)

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
plt.savefig(os.path.join(save_dir, "YOLO_power_comparison.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "YOLO_power_comparison.pdf"), bbox_inches='tight')
plt.close()
