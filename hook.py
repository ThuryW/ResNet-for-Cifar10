import torch
import torch.backends.cudnn as cudnn
import torchvision.transforms as transforms
from torchvision import datasets
from torch.utils.data import DataLoader, Subset
from model.resnet import *
import pandas as pd

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
model = resnet20()
print(f"Using device: {device}")

# 加载训练后的模型权重
checkpoint = torch.load('./checkpoint/20_ckpt_92.23.pth', map_location=device)
# checkpoint = torch.load('./checkpoint/ckpt.pth', map_location=device)

model = model.to(device)
if device == 'cuda':
    model = torch.nn.DataParallel(model)
    cudnn.benchmark = True
    model.load_state_dict(checkpoint['net']) 
else:
    # 如果是 DataParallel 模型，移除 'module.' 前缀
    state_dict = checkpoint['net']
    from collections import OrderedDict
    new_state_dict = OrderedDict()

    for k, v in state_dict.items():
        if k.startswith('module.'):
            new_state_dict[k[7:]] = v  # 去掉 'module.' 前缀
        else:
            new_state_dict[k] = v

    model.load_state_dict(new_state_dict) 

model.eval()  # 切换到评估模式

# 注册钩子函数
def get_linear_input(module, input, output):
    # 打印输入的形状和通道数
    input_tensor = input[0]  # 获取输入张量
    input_shape = input_tensor.shape
    num_features = input_shape[1]  # 对于线性层，特征数是第二个维度
    print("Input Shape:", input_shape)
    print("Number of Features:", num_features)

    # 获取每个特征的输入值
    for feature in range(num_features):
        feature_input = input_tensor[:, feature].detach().cpu().numpy()  # 获取每个特征列的输入
        # print(f"Feature {feature} Input Shape:", feature_input.shape)

        # 计算输入的均值、方差、最大值和最小值
        mean = feature_input.mean()
        variance = feature_input.var()
        max_value = feature_input.max()
        min_value = feature_input.min()
        
        print(f"Feature {feature} Input Max: {max_value:.4f}, Min: {min_value:.4f}, Mean: {mean:.4f}, Variance: {variance:.4f}")



def get_bn_output(module, input, output):
    # 打印输出的形状和通道数
    output_shape = output.shape
    num_channels = output_shape[1]  # 通道数是第二个维度
    print("Output Shape:", output_shape)
    print("Number of Channels:", num_channels)

    # 获取通道0的输出
    for channel in range(num_channels):
        channel_output = output[:, channel, :, :].detach().cpu().numpy()  # 将输出转换为 NumPy 数组
        # print(f"Channel {channel} Batch Norm Output Shape:", channel_output.shape)

        # 计算输出的均值、方差、最大值和最小值
        mean = channel_output.mean()
        variance = channel_output.var()
        max_value = channel_output.max()
        min_value = channel_output.min()
        
        print(f"Channel {channel} Batch Norm Output Max: {max_value:.4f}, Min: {min_value:.4f}, Mean: {mean:.4f}, Variance: {variance:.4f}, ")
    
    
    # # 将数据写入 CSV 文件
    # df = pd.DataFrame(channel_output.reshape(-1, channel_output.shape[2]))  # 展平通道
    # df.to_csv('./hook_files/bn_channel_output.csv', index=False)

def get_layer_output(module, input, output):
    # 打印输出的形状和通道数
    output_shape = output.shape
    num_channels = output_shape[1]  # 通道数是第二个维度
    print("Layer Output Shape:", output_shape)
    print("Number of Channels:", num_channels)

    # 获取通道0的输出
    for channel in range(num_channels):
        channel_output = output[:, channel, :, :].detach().cpu().numpy()  # 将输出转换为 NumPy 数组

        # 计算输出的均值、方差、最大值和最小值
        mean = channel_output.mean()
        variance = channel_output.var()
        max_value = channel_output.max()
        min_value = channel_output.min()
        
        print(f"Channel {channel} Output Max: {max_value:.4f}, Min: {min_value:.4f}, Mean: {mean:.4f}, Variance: {variance:.4f}")


# 绑定钩子到 BN 层
if device == 'cuda':
    hook = model.module.layer1[0].bn1.register_forward_hook(get_bn_output)
else:
    hook = model.bn1.register_forward_hook(get_layer_output)


# 定义 CIFAR-10 数据集的转换
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))  # 标准化
])

# 下载 CIFAR-10 数据集
train_dataset = datasets.CIFAR10(root='./data', train=False, download=False, transform=transform)

# 选择前 227 张图片
subset_indices = list(range(227))
train_subset = Subset(train_dataset, subset_indices)
train_loader = DataLoader(train_subset, batch_size=227, shuffle=False)

# 获取一个批次的数据
dataiter = iter(train_loader)
images, labels = next(dataiter)

# 将数据移动到指定设备
images = images.to(device)

# # 输出 images 中第一张图片第一个通道的前 10 个像素值
# first_image_first_channel_pixels = images[0, 0, :, :].flatten()  # 取第一张图片的第一个通道并扁平化
# print("First image first channel first 10 pixel values:", first_image_first_channel_pixels[:10].cpu().numpy())
# print("")

# 前向传播
with torch.no_grad():  # 不计算梯度
    model(images)

# 移除钩子
hook.remove()
