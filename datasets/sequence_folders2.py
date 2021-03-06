import torch.utils.data as data
import numpy as np
from scipy.misc import imread
from path import Path
import random

'''用于无监督序列生成，主要区别在于文件夹结构匹配

root
    |--seq1
        |--imgs#就用到这里
            |--0000001.jpg
            |--...
        |--depth
            |--...



'''


#这里决定跳帧
def crawl_folders(folders_list, sequence_length,shuffle = False):
        sequence_set = []
        demi_length = (sequence_length-1)//2
        for folder in folders_list:
            intrinsics = np.genfromtxt(folder/'cam.txt', delimiter=',')#分隔符空格
            intrinsics = intrinsics.astype(np.float32).reshape((3, 3))
            imgs = sorted(folder.files('*.jpg'))
            if len(imgs) < sequence_length:
                continue
            for i in range(demi_length, len(imgs)-demi_length):
                sample = {'intrinsics': intrinsics, 'tgt': imgs[i], 'ref_imgs': []}
                for j in range(-demi_length, demi_length + 1):
                    if j != 0:
                        sample['ref_imgs'].append(imgs[i+j])
                sequence_set.append(sample)
        if shuffle:
            random.shuffle(sequence_set)
        else:
            pass
        return sequence_set


def crawl_folders2(folders_list, sequence_length,interval_frame=0,sample_gap = 0, shuffle=False):
    sequence_set = []
    demi_length = (sequence_length - 1) // 2
    for folder in folders_list:
        intrinsics = np.genfromtxt(folder/ 'cam.txt', delimiter=',')  # 分隔符空格
        intrinsics = intrinsics.astype(np.float32).reshape((3, 3))
        imgs = sorted((folder/'imgs').files('*.jpg'))
        if len(imgs) < sequence_length:#frame太少, 放弃这个folder
            continue
        #插孔抽出
        for i in range(len(imgs)):
            if i % (interval_frame+1) != 0 :
                imgs[i]=None
        while None in imgs:
            imgs.remove(None)

        for i in range(demi_length, len(imgs) - demi_length):#在一个folder里
            sample = {'intrinsics': intrinsics, 'tgt': imgs[i], 'ref_imgs': []}
            for j in range(-demi_length, demi_length + 1):
                if j != 0:
                    sample['ref_imgs'].append(imgs[i + j])
            sequence_set.append(sample)



    if shuffle:
        random.shuffle(sequence_set)
    else:
        pass

    # 插空减少样本，提升训练速度
    for i in range(len(sequence_set)):
        if i % (sample_gap+1) != 0:
            sequence_set[i] = None
    while None in sequence_set:
        sequence_set.remove(None)


    return sequence_set


def load_as_float(path):
    return imread(path).astype(np.float32)


class SequenceFolder(data.Dataset):
    """A sequence data loader where the files are arranged in this way:
        root/scene_1/0000000.jpg
        root/scene_1/0000001.jpg
        ..
        root/scene_1/cam.txt
        root/scene_2/0000000.jpg
        .

        transform functions must take in a list a images and a numpy array (usually intrinsics matrix)
    """

    def __init__(self, root, seed=None, train=True, sequence_length=3, transform=None, target_transform=None):
        np.random.seed(seed)
        random.seed(seed)
        self.root = Path(root)
        scene_list_path = self.root/'train.txt' if train else self.root/'val.txt'
        self.scenes = [self.root/folder[:-1] for folder in open(scene_list_path)]
        if train:
            self.samples = crawl_folders2(self.scenes, sequence_length,interval_frame=0,sample_gap=0,shuffle=True)
        else:
            self.samples = crawl_folders2(self.scenes, sequence_length,interval_frame=0,sample_gap=0,shuffle=False)
        self.transform = transform


    def __getitem__(self, index):
        sample = self.samples[index]
        tgt_img = load_as_float(sample['tgt'])
        ref_imgs = [load_as_float(ref_img) for ref_img in sample['ref_imgs']]
        if self.transform is not None:
            imgs, intrinsics = self.transform([tgt_img] + ref_imgs, np.copy(sample['intrinsics']))
            tgt_img = imgs[0]
            ref_imgs = imgs[1:]
        else:
            intrinsics = np.copy(sample['intrinsics'])
        return tgt_img, ref_imgs, intrinsics, np.linalg.inv(intrinsics)

    def __len__(self):
        return len(self.samples)
