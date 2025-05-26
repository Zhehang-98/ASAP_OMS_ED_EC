import matplotlib.pyplot as plt
import os
from matplotlib.transforms import offset_copy

# 保存目录
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# 数据
lambda_comp = list(range(1, 11))
rpi5_ec = [111,188,286,398,500,594,662,692,683,709]
rpi5_ed = [0,0,0,0,0,9,38,62,194,275]
qidk_ec = [104,189,286,395,477,583,687,675,758,733]
qidk_ed = [0,0,0,0,0,12,30,71,227,262]


rpi5_ec_ips = [x / 100.0 for x in rpi5_ec]
rpi5_ed_ips = [x / 100.0 for x in rpi5_ed]
qidk_ec_ips = [x / 100.0 for x in qidk_ec]
qidk_ed_ips = [x / 100.0 for x in qidk_ed]

# 设置字体大小
plt.rcParams.update({'font.size': 16})

# 自定义偏移（你可以在这里修改以微调每个点的标注）

offsets_rpi5_ec = [(-3, 10),  (15, -15),  (-10, 10),  (-10, 10),  (-12, 10),  (-12, 10),
                (0, -15),  (0,10),  (0, -15),  (0, -15)]
offsets_qidk_ec = [(3, -15),   (-10, 10),  (15, -15) ,   (15, -15),   (15, -15) , (15, -15),
                (0, 10), (0, -15), (0, 10), (0, 10)]
offsets_rpi5_ed = [(0, 10),   (0, 10),     (0, 10),     (0, 10),     (0, -15),     (3, -15),
                (0, 10),  (0, -15), (3, -15),    (-3, 10)]
offsets_qidk_ed = [(0, -15),   (0, -15),   (0, -15), (0, -15), (0, 10), (3, 10),
                (0, -15), (-5, 10), (-3, 10),    (3, -15)]

plt.figure(figsize=(12, 6))
split_index = lambda_comp.index(10)

# 前半段（实线）
plt.plot(lambda_comp[:split_index+1], rpi5_ec_ips[:split_index+1],
         marker='o', color='red', linestyle='-', label='RPI5 EC')
plt.plot(lambda_comp[:split_index+1], qidk_ec_ips[:split_index+1],
         marker='s', color='blue', linestyle='-', label='QIDK EC')

plt.plot(lambda_comp[:split_index+1], rpi5_ed_ips[:split_index+1],
         marker='o', color='darkgreen', linestyle='-', label='RPI5 ED', alpha=0.8)
plt.plot(lambda_comp[:split_index+1], qidk_ed_ips[:split_index+1],
         marker='s', color='indigo', linestyle='-', label='QIDK ED', alpha=0.6)



# 标注文字
for i, x in enumerate(lambda_comp):
    # EC 标注
    offset_x_rpi5_ec, offset_y_rpi5_ec = offsets_rpi5_ec[i]
    offset_x_qidk_ec, offset_y_qidk_ec = offsets_qidk_ec[i]
    trans_rpi5_ec = offset_copy(plt.gca().transData, fig=plt.gcf(),
                                x=offset_x_rpi5_ec, y=offset_y_rpi5_ec, units='points')
    trans_qidk_ec = offset_copy(plt.gca().transData, fig=plt.gcf(),
                                x=offset_x_qidk_ec, y=offset_y_qidk_ec, units='points')
    plt.text(x, rpi5_ec_ips[i], f"{rpi5_ec_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_rpi5_ec)
    plt.text(x, qidk_ec_ips[i], f"{qidk_ec_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_qidk_ec)

    # ED 标注
    offset_x_rpi5_ed, offset_y_rpi5_ed = offsets_rpi5_ed[i]
    offset_x_qidk_ed, offset_y_qidk_ed = offsets_qidk_ed[i]
    trans_rpi5_ed = offset_copy(plt.gca().transData, fig=plt.gcf(),
                                x=offset_x_rpi5_ed, y=offset_y_rpi5_ed, units='points')
    trans_qidk_ed = offset_copy(plt.gca().transData, fig=plt.gcf(),
                                x=offset_x_qidk_ed, y=offset_y_qidk_ed, units='points')
    plt.text(x, rpi5_ed_ips[i], f"{rpi5_ed_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_rpi5_ed)
    plt.text(x, qidk_ed_ips[i], f"{qidk_ed_ips[i]:.2f}", ha='center',
             fontsize=12, transform=trans_qidk_ed)

    

# λ = 40 的垂直线
plt.axvline(x=6, color='gray', linestyle='--')
plt.text(6.6, 2, 'Breakpoint: λ = 6', fontsize=12, va='center', ha='right', color='gray')

# 插入这里
plt.axvline(x=10, color='black', linestyle=':', linewidth=1)

plt.xticks(range(0, 11, 1))

# 单独把 x=10 的刻度变颜色
ax = plt.gca()
for label in ax.get_xticklabels():
    if label.get_text() == "10":
        label.set_color("darkorange")

plt.xlim(0, 11)

# y 轴按比例扩展上下边距
all_vals = rpi5_ec_ips + rpi5_ed_ips + qidk_ec_ips + qidk_ed_ips
y_min, y_max = min(all_vals), max(all_vals)
margin = (y_max - y_min) * 0.1
plt.ylim(y_min - margin, y_max + margin)

# 其他设置
plt.xlabel("λ", fontsize=16)
plt.ylabel("Requests per second", fontsize=16)
plt.legend()
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

# 保存图像
plt.savefig(os.path.join(save_dir, "YOLO_request_comparison.png"), bbox_inches='tight')
plt.savefig(os.path.join(save_dir, "YOLO_request_comparison.pdf"), bbox_inches='tight')
plt.close()
