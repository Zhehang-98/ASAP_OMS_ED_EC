import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 创建保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# 数据
lambda_comp = list(range(1, 14))
rpi5_energy = [62.52561,72.13508,74.643556,92.612169,102.36506,216.5692,
466.64089536,662.92387757,1832.78795784,1643.10468966,1590.98747535,1525.3509392,1464.27410569]
qidk_energy = [55.90728,53.929814,60.472348,86.350509,86.417136,261.331756,
308.7754353,522.04485088,1618.27473688,1850.42921262,1918.0864101,1898.76445311,1997.4267724]




# 自定义偏移（你可以改这些来控制标注位置）
# 设置每个点的标注偏移（单位为 points），分别为 (x, y)
offsets_rpi5 = [(0, 10), (0, 10), (0, 10), (0, 10), (0, 10), (-3, -20),
                (-7, 15), (-17, 15), (-14, 10), (0, -15), (-3, 10), (0, 7), (0,-15)]
offsets_qidk = [(0, -15), (0, -15), (0, -15), (0, -15), (0, -15), (-3, 15),
                (0, -15), (14, -15), (17, -25), (0, 15), (0, 15), (0, 10), (0,15)]

# 设置全局字体大小
plt.rcParams.update({'font.size': 16})

split_index = lambda_comp.index(10)

# 前半段（实线）
plt.plot(lambda_comp[:split_index+1], rpi5_energy[:split_index+1],
         marker='o', color='red', linestyle='-', label='RPI5')
plt.plot(lambda_comp[:split_index+1], qidk_energy[:split_index+1],
         marker='s', color='blue', linestyle='-', label='QIDK')

# 后半段（虚线）
plt.plot(lambda_comp[split_index:], rpi5_energy[split_index:],
         marker='o', color='red', linestyle='--')
plt.plot(lambda_comp[split_index:], qidk_energy[split_index:],
         marker='s', color='blue', linestyle='--')
# 画图
plt.figure(figsize=(12, 6))
plt.plot(lambda_comp, rpi5_energy, marker='o', color='red', label='RPI5')
plt.plot(lambda_comp, qidk_energy, marker='s', color='blue', label='QIDK')

# 添加数字标注
for i, x in enumerate(lambda_comp):
    offset_x_rpi5, offset_y_rpi5 = offsets_rpi5[i]
    offset_x_qidk, offset_y_qidk = offsets_qidk[i]

    trans_rpi5 = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_rpi5, y=offset_y_rpi5, units='points')
    trans_qidk = offset_copy(plt.gca().transData, fig=plt.gcf(),
                             x=offset_x_qidk, y=offset_y_qidk, units='points')

    plt.text(x, rpi5_energy[i], f"{rpi5_energy[i]:.2f}", ha='center',
             fontsize=12, transform=trans_rpi5)
    plt.text(x, qidk_energy[i], f"{qidk_energy[i]:.2f}", ha='center',
             fontsize=12, transform=trans_qidk)
    
# λ = 40 的垂直线
plt.axvline(x=6, color='gray', linestyle='--')
plt.text(6.75, 1000, 'Breakpoint: λ = 6', fontsize=12, va='center', ha='right', color='gray')

# 插入这里
plt.axvline(x=10, color='black', linestyle=':', linewidth=1)


# 横坐标设置
plt.xticks(range(0, 14, 1))


# 单独把 x=10 的刻度变颜色
ax = plt.gca()
for label in ax.get_xticklabels():
    if label.get_text() == "10":
        label.set_color("darkorange")

plt.xlim(0, 14)
# 设置 x 轴刻度：在默认 range 里手动加上 57

# 设置纵坐标：上下各加 15%
y_all = rpi5_energy + qidk_energy
y_min, y_max = min(y_all), max(y_all)
margin = (y_max - y_min) * 0.1
plt.ylim(y_min - margin, y_max + margin)

# 标签 & 样式
plt.xlabel("λ", fontsize=16)
plt.ylabel("Energy per image (mJ)", fontsize=16)
plt.legend()
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

# 保存图像
plt.savefig(os.path.join(save_dir, "YOLO_energy_comparison.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "YOLO_energy_comparison.pdf"), bbox_inches='tight')
plt.close()
