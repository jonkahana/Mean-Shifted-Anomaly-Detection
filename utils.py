import torch
import torchvision
import torchvision.transforms as transforms
import numpy as np
from os.path import join
from torch.utils.data import Dataset, DataLoader
import faiss
import PIL
import torchvision.models as models
import torch.nn.functional as F
from PIL import ImageFilter
import random
from torchvision.transforms import InterpolationMode

BICUBIC = InterpolationMode.BICUBIC
preprocessed_dir = '/cs/labs/yedid/jonkahana/projects/Red_PANDA/cache/preprocess'


class transform_NumpytoPIL(torch.nn.Module):

    def __init__(self):
        super().__init__()

    def __call__(self, img: torch.Tensor):
        """
        Args:
            img (torch.Tensor): Tensor image to be converted to numpy.array
        Returns:
            img (numpy.array): numpy image.
        """
        if np.max(img) <= 1:
            img = (img * 255.).astype(np.uint8)
        if img.shape[0] in [1, 3]:
            img = img.transpose(1, 2, 0)
        if img.shape[-1] == 1:
            img = np.concatenate([img] * 3, axis=-1)
        return PIL.Image.fromarray(img)

class GaussianBlur(object):
    """Gaussian blur augmentation in SimCLR https://arxiv.org/abs/2002.05709"""

    def __init__(self, sigma=[.1, 2.]):
        self.sigma = sigma

    def __call__(self, x):
        sigma = random.uniform(self.sigma[0], self.sigma[1])
        x = x.filter(ImageFilter.GaussianBlur(radius=sigma))
        return x


transform_color = transforms.Compose([
    transform_NumpytoPIL(),
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])

transform_resnet18 = transforms.Compose([
    transform_NumpytoPIL(),
    transforms.Resize(224, interpolation=BICUBIC),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

moco_transform = transforms.Compose([
    transform_NumpytoPIL(),
    transforms.RandomResizedCrop(224, scale=(0.2, 1.)),
    transforms.RandomApply([
        transforms.ColorJitter(0.4, 0.4, 0.4, 0.1)  # not strengthened
    ], p=0.8),
    transforms.RandomGrayscale(p=0.2),
    transforms.RandomApply([GaussianBlur([.1, 2.])], p=0.5),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])


class Transform(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.moco_transform = transforms.Compose([
            transform_NumpytoPIL(),
            transforms.RandomResizedCrop(224, scale=(0.2, 1.)),
            transforms.RandomApply([
                transforms.ColorJitter(0.4, 0.4, 0.4, 0.1)  # not strengthened
            ], p=0.8),
            transforms.RandomGrayscale(p=0.2),
            transforms.RandomApply([GaussianBlur([.1, 2.])], p=0.5),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]
        )

    def __call__(self, x):
        x_1 = self.moco_transform(x)
        x_2 = self.moco_transform(x)
        return x_1, x_2


class Model(torch.nn.Module):
    def __init__(self, backbone):
        super().__init__()
        if backbone == 152:
            self.backbone = models.resnet152(pretrained=True)
        elif backbone == 50:
            self.backbone = models.resnet50(pretrained=True)
        else:
            self.backbone = models.resnet18(pretrained=True)
        self.backbone.fc = torch.nn.Identity()
        freeze_parameters(self.backbone, backbone, train_fc=False)

    def forward(self, x):
        z1 = self.backbone(x)
        z_n = F.normalize(z1, dim=-1)
        return z_n


def freeze_parameters(model, backbone, train_fc=False):
    if not train_fc:
        for p in model.fc.parameters():
            p.requires_grad = False
    if backbone == 152:
        for p in model.conv1.parameters():
            p.requires_grad = False
        for p in model.bn1.parameters():
            p.requires_grad = False
        for p in model.layer1.parameters():
            p.requires_grad = False
        for p in model.layer2.parameters():
            p.requires_grad = False


def knn_score(train_set, test_set, n_neighbours=2):
    """
    Calculates the KNN distance
    """
    index = faiss.IndexFlatL2(train_set.shape[1])
    index.add(train_set)
    D, _ = index.search(test_set, n_neighbours)
    return np.sum(D, axis=1)


def get_loaders(dataset, label_class, batch_size, backbone):
    if dataset == "cifar10":
        ds = torchvision.datasets.CIFAR10
        transform = transform_color if backbone == 152 else transform_resnet18
        coarse = {}
        trainset = ds(root='data', train=True, download=True, transform=transform, **coarse)
        testset = ds(root='data', train=False, download=True, transform=transform, **coarse)
        trainset_1 = ds(root='data', train=True, download=True, transform=Transform(), **coarse)
        idx = np.array(trainset.targets) == label_class
        testset.targets = [int(t != label_class) for t in testset.targets]
        trainset.data = trainset.data[idx]
        trainset.targets = [trainset.targets[i] for i, flag in enumerate(idx, 0) if flag]
        trainset_1.data = trainset_1.data[idx]
        trainset_1.targets = [trainset_1.targets[i] for i, flag in enumerate(idx, 0) if flag]
        train_loader = torch.utils.data.DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=2,
                                                   drop_last=False)
        test_loader = torch.utils.data.DataLoader(testset, batch_size=batch_size, shuffle=False, num_workers=2,
                                                  drop_last=False)
        return train_loader, test_loader, torch.utils.data.DataLoader(trainset_1, batch_size=batch_size,
                                                                      shuffle=True, num_workers=2, drop_last=False)
    else:
        print('Unsupported Dataset')
        exit()


def load_np_data(data_name):
    data = dict(np.load(join(preprocessed_dir, data_name + '.npz'), allow_pickle=True))
    data['n_classes'] = len(np.unique(data['classes']))
    imgs = data['imgs'].astype(np.float32)
    imgs = imgs / 255.0
    data['imgs'] = imgs
    return data


class Images_Data(Dataset):

    def __init__(self, data, transform=transforms.ToTensor()):
        self.imgs = data['imgs']
        self.labels = data['anom_label']
        self.transform = transform

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, index):
        return self.transform(self.imgs[index]), torch.tensor(int(self.labels[index]))


def get_npz_loaders(dataset, batch_size):
    train_np_data = load_np_data(join(preprocessed_dir, dataset))
    test_np_data = load_np_data(join(preprocessed_dir, dataset.replace('train', 'test')))
    test_np_data['anom_label'] = (test_np_data['anom_label'] == 1).astype(int)

    train_data = Images_Data(train_np_data, transform=transform_color)
    train_data_1 = Images_Data(train_np_data, transform=Transform())
    test_data = Images_Data(test_np_data, transform=transform_color)

    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, num_workers=2, drop_last=False)
    train_loader_1 = DataLoader(train_data_1, batch_size=batch_size, shuffle=True, num_workers=2, drop_last=False)
    test_loader = DataLoader(test_data, batch_size=batch_size, shuffle=False, num_workers=2, drop_last=False)
    return train_loader, test_loader, train_loader_1
