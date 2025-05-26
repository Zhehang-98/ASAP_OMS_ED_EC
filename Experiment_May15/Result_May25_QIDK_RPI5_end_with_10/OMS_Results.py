import matplotlib.pyplot as plt
import os
import numpy as np
from matplotlib.transforms import offset_copy


# Prepare save directory
save_dir = "Paper_Result_Analysis"
os.makedirs(save_dir, exist_ok=True)

# ========================
# 1. RPI5 Independent Data for yolov5s
# ========================
lambda_rpi5_ind = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
rpi5_ec_ind = [211, 389, 632, 793, 1009, 1135, 1307, 1398, 1445, 1445]
rpi5_ed_ind = [0, 0, 0, 0, 2, 19, 87, 212, 303, 551]
rpi5_lat_ind = [125, 132, 152, 160, 203, 261, 393, 1053, 1861, 3975]
rpi5_energy_ind = [5.5759, 5.7403, 5.8636, 6.0965, 7.5624, 229.158, 748.0207, 1505.7594, 1751.14302, 1821.3354]
rpi5_ec_ips_ind = [x / 100.0 for x in rpi5_ec_ind]
rpi5_ed_ips_ind = [x / 100.0 for x in rpi5_ed_ind]

# ========================
# 5. Competing Data for ResNet50
# ========================
lambda_resnet = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 57]
resnet_rpi5_ec = [500, 1029, 1479, 1983, 2544, 3101, 3359, 4097, 4405, 4848, 4871, 4642]
resnet_rpi5_ed = [0, 0, 0, 0, 0, 0, 0, 3, 49, 237, 617, 993]
resnet_qidk_ec = [495, 1056, 1092, 1997, 2523, 2980, 3597, 3911, 4543, 4583, 4718, 4745]
resnet_qidk_ed = [0, 0, 0, 0, 0, 0, 0, 2, 36, 240, 623, 988]
resnet_rpi5_latency = [36, 36, 37, 38, 41, 44, 50, 60, 97, 150, 282, 1358]
resnet_qidk_latency = [51, 48, 48, 50, 52, 55, 60, 72, 105, 149, 251, 989]
resnet_rpi5_energy = [9.36, 10.44, 11.47, 12.92, 15.17, 17.6, 21, 30.6, 103.79, 330.2, 641.35, 685.419]
resnet_qidk_energy = [1.56111, 1.75392, 1.80864, 2.4265, 1.7654, 2.2726, 1.992, 2.73024, 3.44295, 3.66012, 4.10724, 7.369596]

resnet_rpi5_ec_ips = [x / 100.0 for x in resnet_rpi5_ec]
resnet_rpi5_ed_ips = [x / 100.0 for x in resnet_rpi5_ed]
resnet_qidk_ec_ips = [x / 100.0 for x in resnet_qidk_ec]
resnet_qidk_ed_ips = [x / 100.0 for x in resnet_qidk_ed]


# ================
# 2. Competing Data for yolov5s
# ================
lambda_comp = list(range(1, 11))
rpi5_ec = [80, 194, 308, 420, 510, 557, 658, 704, 722, 746]
rpi5_ed = [0, 0, 0, 0, 0, 3, 30, 82, 178, 242]
qidk_ec = [97, 180, 316, 389, 473, 554, 668, 730, 744, 734]
qidk_ed = [0, 0, 0, 0, 0, 6, 21, 89, 158, 276]
rpi5_energy = [37.944, 49.256, 60.4, 72.275, 83.6, 128.453, 359.97, 741.3952, 1346.98676, 1600.4156]
qidk_energy = [7.61402, 4.52893, 4.9962, 6.65658, 6.56552, 8.1719, 15.089805, 8.9574327, 10.00127385, 8.65190304]
rpi5_latency = [124, 131, 151, 175, 200, 241, 338, 489, 730, 1367]
qidk_latency = [158, 161, 165, 189, 214, 253, 347, 615, 804, 2329]
rpi5_ec_ips = [x / 100.0 for x in rpi5_ec]
rpi5_ed_ips = [x / 100.0 for x in rpi5_ed]
qidk_ec_ips = [x / 100.0 for x in qidk_ec]
qidk_ed_ips = [x / 100.0 for x in qidk_ed]

# ========================
# Color scheme
# ========================
COLOR_RPI5_EC = 'red'
COLOR_RPI5_ED = 'lightcoral'
COLOR_QIDK_EC = 'blue'
COLOR_QIDK_ED = 'skyblue'

# Set font size globally
plt.rcParams.update({'font.size': 12})

# Helper Functions
def annotate_multiple_lines(x_list, y_lists, fmt="{:.1f}", offset_pixel=10, min_diff_ratio=0.005):


    ax = plt.gca()
    y_max = max(max(ys) for ys in y_lists)
    min_diff = y_max * min_diff_ratio

    for i, x in enumerate(x_list):
        ys_at_x = [(idx, ys[i]) for idx, ys in enumerate(y_lists)]
        # Sort by y-value to identify relative position
        ys_at_x.sort(key=lambda item: item[1])

        used_levels = set()
        for rank, (idx, y_val) in enumerate(ys_at_x):
            # Find available offset level
            level = 0
            while level in used_levels or -level in used_levels:
                level += 1
            # Use symmetric spacing: 0, +1, -1, +2, -2, ...
            offset_level = -level if rank % 2 == 0 else level
            used_levels.add(offset_level)

            # Always offset from point, never put label on the point
            final_offset = offset_pixel * (offset_level if offset_level != 0 else 1)

            # Apply transform with offset
            trans = offset_copy(ax.transData, fig=ax.figure,
                                y=final_offset, units='points')
            plt.text(x, y_val, fmt.format(y_val), ha='center',
                     fontsize=11, transform=trans)


def mark_breakpoint(x, y):
    plt.axvline(x=x, color='gray', linestyle='--')
    plt.text(x + 0.2, y, f'λ = {x}', rotation=0, fontsize=12)

def save_fig(name):
    path = os.path.join(save_dir, name)
    plt.savefig(path + ".png", bbox_inches='tight')
    plt.savefig(path + ".pdf", bbox_inches='tight')
    plt.close()

def setup_axis(model, y_data=None, y_pad_ratio=0.1):
    if model == "resnet":
        plt.xticks(range(0, 65, 5))
        plt.xlim(0, 60)
    elif model == "yolo":
        plt.xticks(range(0, 12, 1))
        plt.xlim(0, 11)

    if y_data:
        y_max = max(y_data)
        y_min = min(y_data)
        margin = (y_max - y_min) * y_pad_ratio
        plt.ylim(y_min - margin, y_max + margin)



# ========================
# 4. Competing Comparison for yolo v5s
# ========================

# YOLOv5s Competing - Throughput
plt.figure(figsize=(12, 6))
plt.plot(lambda_comp, rpi5_ec_ips, marker='o', color=COLOR_RPI5_EC, label='RPI5 EC')
plt.plot(lambda_comp, qidk_ec_ips, marker='s', color=COLOR_QIDK_EC, label='QIDK EC')
plt.plot(lambda_comp, rpi5_ed_ips, marker='o', color=COLOR_RPI5_ED, label='RPI5 ED')
plt.plot(lambda_comp, qidk_ed_ips, marker='s', color=COLOR_QIDK_ED, label='QIDK ED')
annotate_multiple_lines(lambda_comp, [rpi5_ec_ips, rpi5_ed_ips, qidk_ec_ips, qidk_ed_ips])
setup_axis("yolo", rpi5_ec_ips + rpi5_ed_ips + qidk_ec_ips + qidk_ed_ips)
mark_breakpoint(x=6, y=4.8)
plt.xlabel("λ")
plt.ylabel("Images per second")
plt.legend()
plt.grid(True)
save_fig("YOLO_throughput_comparison")

# YOLOv5s Competing - Latency
plt.figure(figsize=(12, 6))
plt.plot(lambda_comp, rpi5_latency, marker='o', color=COLOR_RPI5_EC, label='RPI5')
plt.plot(lambda_comp, qidk_latency, marker='s', color=COLOR_QIDK_EC, label='QIDK')
annotate_multiple_lines(lambda_comp, [rpi5_latency, qidk_latency], fmt="{}")
setup_axis("yolo", rpi5_latency + qidk_latency)
mark_breakpoint(x=6, y=1367)
plt.xlabel("λ")
plt.ylabel("Round Trip Delay (ms)")
plt.legend()
plt.grid(True)
save_fig("YOLO_latency_comparison")

# YOLOv5s Competing - Energy
plt.figure(figsize=(12, 6))
plt.plot(lambda_comp, rpi5_energy, marker='o', color=COLOR_RPI5_EC, label='RPI5')
plt.plot(lambda_comp, qidk_energy, marker='s', color=COLOR_QIDK_EC, label='QIDK')
annotate_multiple_lines(lambda_comp, [rpi5_energy, qidk_energy], fmt="{:.1f}")
setup_axis("yolo", rpi5_energy + qidk_energy)
mark_breakpoint(x=6, y=1600)
plt.xlabel("λ")
plt.ylabel("Energy per image (mJ)")
plt.legend()
plt.grid(True)
save_fig("YOLO_energy_comparison")

# ResNet50 Competing - Throughput
plt.figure(figsize=(12, 6))
plt.plot(lambda_resnet, resnet_rpi5_ec_ips, marker='o', color=COLOR_RPI5_EC, label='RPI5 EC')
plt.plot(lambda_resnet, resnet_qidk_ec_ips, marker='s', color=COLOR_QIDK_EC, label='QIDK EC')
plt.plot(lambda_resnet, resnet_rpi5_ed_ips, marker='o', color=COLOR_RPI5_ED, label='RPI5 ED')
plt.plot(lambda_resnet, resnet_qidk_ed_ips, marker='s', color=COLOR_QIDK_ED, label='QIDK ED')
annotate_multiple_lines(lambda_resnet, [resnet_rpi5_ec_ips, resnet_rpi5_ed_ips, resnet_qidk_ec_ips, resnet_qidk_ed_ips])
setup_axis("resnet", resnet_rpi5_ec_ips + resnet_rpi5_ed_ips + resnet_qidk_ec_ips + resnet_qidk_ed_ips)
mark_breakpoint(x=40, y=40)
plt.xlabel("λ")
plt.ylabel("Images per second")
plt.legend()
plt.grid(True)
save_fig("resnet50_competing_throughput")

# ResNet50 Competing - Latency
plt.figure(figsize=(12, 6))
plt.plot(lambda_resnet, resnet_rpi5_latency, marker='o', color=COLOR_RPI5_EC, label='RPI5')
plt.plot(lambda_resnet, resnet_qidk_latency, marker='s', color=COLOR_QIDK_EC, label='QIDK')
annotate_multiple_lines(lambda_resnet, [resnet_rpi5_latency, resnet_qidk_latency], fmt="{}")
setup_axis("resnet", resnet_rpi5_latency + resnet_qidk_latency)
mark_breakpoint(x=40, y=1358)
plt.xlabel("λ")
plt.ylabel("Round Trip Delay (ms)")
plt.legend()
plt.grid(True)
save_fig("resnet50_competing_latency")

# ResNet50 Competing - Energy
plt.figure(figsize=(12, 6))
plt.plot(lambda_resnet, resnet_rpi5_energy, marker='o', color=COLOR_RPI5_EC, label='RPI5')
plt.plot(lambda_resnet, resnet_qidk_energy, marker='s', color=COLOR_QIDK_EC, label='QIDK')
annotate_multiple_lines(lambda_resnet, [resnet_rpi5_energy, resnet_qidk_energy], fmt="{:.1f}")
setup_axis("resnet", resnet_rpi5_energy + resnet_qidk_energy)
mark_breakpoint(x=40, y=685)
plt.xlabel("λ")
plt.ylabel("Energy per image (mJ)")
plt.legend()
plt.grid(True)
save_fig("resnet50_competing_energy")
