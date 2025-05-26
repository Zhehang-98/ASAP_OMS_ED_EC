import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 创建保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# 数据
lambda_comp = list(range(1, 11))
rpi5_latency = [126,136,139,169,188,262,368,396,884,1796]
qidk_latency = [156,157,163,189,201,389,469,473,2337,3631]




# 设置每个点的标注偏移（单位为 points），分别为 (x, y)
offsets_rpi5 = [(0, -15), (0, -15), (0, -15), (0, -15), (0, -15), (0, -15),
                (0, -15), (0, -15), (0, -15), (0, 10)]
offsets_qidk = [(0, 10), (0, 10), (0, 10), (0, 10), (0, 10), (0, 10),
                (0, 10), (-10, 10), (-13, 13), (0, 10)]



# 设置字体
plt.rcParams.update({'font.size': 16})

# 画图
plt.figure(figsize=(12, 6))
plt.plot(lambda_comp, rpi5_latency, marker='o', color='red', label='RPI5')
plt.plot(lambda_comp, qidk_latency, marker='s', color='blue', label='QIDK')

# 添加标注，每个点可以自定义偏移
# 添加标注
for i, x in enumerate(lambda_comp):
    offset_x_rpi5, offset_y_rpi5 = offsets_rpi5[i]
    offset_x_qidk, offset_y_qidk = offsets_qidk[i]

    trans_rpi5 = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_rpi5, y=offset_y_rpi5, units='points')
    trans_qidk = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_qidk, y=offset_y_qidk, units='points')

    plt.text(x, rpi5_latency[i], f"{rpi5_latency[i]}", ha='center',
             fontsize=12, transform=trans_rpi5)
    plt.text(x, qidk_latency[i], f"{qidk_latency[i]}", ha='center',
             fontsize=12, transform=trans_qidk)
    
# λ = 40 的垂直线
plt.axvline(x=6, color='gray', linestyle='--')
plt.text(6.56, 3000, 'Breakpoint: λ = 6', fontsize=12, va='center', ha='right', color='gray')


# 坐标轴设置
plt.xticks(range(0, 12, 1))


# 单独把 x=10 的刻度变颜色
ax = plt.gca()
for label in ax.get_xticklabels():
    if label.get_text() == "10":
        label.set_color("darkorange")

plt.xlim(0, 11)

# y轴自动上下扩 15%
y_all = rpi5_latency + qidk_latency
y_min, y_max = min(y_all), max(y_all)
margin = (y_max - y_min) * 0.1
plt.ylim(y_min - margin, y_max + margin)

# 标签
plt.xlabel("λ", fontsize=16)
plt.ylabel("Avg Inference Time (ms)", fontsize=16)
plt.legend()
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

# 保存图像
plt.savefig(os.path.join(save_dir, "YOLO_latency_comparison.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "YOLO_latency_comparison.pdf"), bbox_inches='tight')
plt.close()
