from __future__ import print_function
import os, sys
import torch
import torch.optim as optim
import torch.backends.cudnn as cudnn
from adamp import AdamP, SGDP
import argparse
import torch.utils.data as data
from data import WiderFaceDetection, detection_collate, preproc, cfg_mnet, cfg_re50, cfg_efb2, cfg_vov39
from layers.modules import MultiBoxLoss
from layers.functions.prior_box import PriorBox
import time
import datetime
import math
from models.retinaface import RetinaFace

parser = argparse.ArgumentParser(description='Retinaface Training')
parser.add_argument('--training_dataset', default='./data/widerface/train/label.txt', help='Training dataset directory')
parser.add_argument('--network', default='efficientb2', help='Backbone network mobile0.25 or resnet50')
parser.add_argument('--num_workers', default=4, type=int, help='Number of workers used in dataloading')
parser.add_argument('--lr', '--learning-rate', default=1e-3, type=float, help='initial learning rate')
parser.add_argument('--momentum', default=0.9, type=float, help='momentum')
parser.add_argument('--resume_net', default=False, help='resume net for retraining')
parser.add_argument('--resume_epoch', default=0, type=int, help='resume iter for retraining')
parser.add_argument('--weight_decay', default=5e-4, type=float, help='Weight decay for SGD')
parser.add_argument('--gamma', default=0.1, type=float, help='Gamma update for SGD')
parser.add_argument('--save_folder', default='./weights/', help='Location to save checkpoint models')
parser.add_argument('--optimizer', default='sgd', help='optimizer for train, sgd, sgdp, or admap')

args = parser.parse_args()

if not os.path.exists(args.save_folder):
    os.mkdir(args.save_folder)
#cfg = None
if args.network == "mobile0.25":
    cfg = cfg_mnet
elif args.network == "resnet50":
    cfg = cfg_re50
elif args.network == "efficientb2":
    cfg = cfg_efb2
elif args.network == "vovnet39b":
    cfg = cfg_vov39
else:
    print("Invalid network!!")
    raise ValueError

rgb_mean = (104, 117, 123) # bgr order
num_classes = 2
img_dim = cfg['image_size']
#num_gpu = cfg['ngpu']
batch_size = cfg['batch_size']
max_epoch = cfg['epoch']
gpu_train = cfg['gpu_train']

num_workers = args.num_workers
momentum = args.momentum
weight_decay = args.weight_decay
initial_lr = args.lr
gamma = args.gamma
training_dataset = args.training_dataset
save_folder = args.save_folder

net = RetinaFace(cfg=cfg)

if gpu_train:
    print("Using GPU: ", torch.cuda.get_device_name(0))
else:
    print("Using CPU")
#print("Printing net...")
#print(net)

#if args.resume_net is not None:
if args.resume_net:
    print('Loading resume network...')
    #state_dict = torch.load(args.resume_net)
    state_dict = torch.load(save_folder + cfg['name']+ '_optim_'+ args.optimizer +'_epoch_' + str(args.resume_epoch-1) + '.pth')
    # create new OrderedDict that does not contain `module.`
    from collections import OrderedDict
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        head = k[:7]
        if head == 'module.':
            name = k[7:] # remove `module.`
        else:
            name = k
        new_state_dict[name] = v
    net.load_state_dict(new_state_dict)

#if num_gpu >= 1 and gpu_train:
if gpu_train:
    net = torch.nn.DataParallel(net).cuda()
else:
    net = net.cpu()

cudnn.benchmark = True

if args.optimizer == 'sgd':
    optimizer = optim.SGD(net.parameters(), lr=initial_lr, momentum=momentum, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, max_epoch, last_epoch=args.resume_epoch-1)
elif args.optimizer == 'sgdp':
    optimizer = SGDP(net.parameters(), lr=initial_lr, momentum=momentum, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, max_epoch)
elif args.optimizer == 'adamp':
    optimizer = AdamP(net.parameters(), lr=initial_lr, weight_decay=weight_decay, last_epoch=args.resume_epoch-1)
    scheduler = None
else:
    print("Invalid optimizer!!")
    raise ValueError

print("Optimizer : ", args.optimizer,"\n")
criterion = MultiBoxLoss(num_classes, 0.35, True, 0, True, 7, 0.35, False, gpu_train)

priorbox = PriorBox(cfg, image_size=(img_dim, img_dim))
with torch.no_grad():
    priors = priorbox.forward()
    #if num_gpu >= 1 and gpu_train:
    if gpu_train:
        priors = priors.cuda()
    else:
        priors = priors.cpu()

def train():
    net.train()
    epoch = 0 + args.resume_epoch
    info = '\rLoading Dataset...'
    sys.stdout.write(info)
    dataset = WiderFaceDetection(training_dataset, preproc(img_dim, rgb_mean))
    info += ' Dataset Ready.\n'
    sys.stdout.write(info)

    epoch_size = math.ceil(len(dataset) / batch_size) # cantidad de batches
    max_iter = max_epoch * epoch_size

    #stepvalues = (cfg['decay1'] * epoch_size, cfg['decay2'] * epoch_size)
    #step_index = 0

    if args.resume_epoch > 0:
        start_iter = args.resume_epoch * epoch_size
    else:
        start_iter = 0
    print("\nTraining Status :")
    for iteration in range(start_iter, max_iter):
        if iteration % epoch_size == 0:
            # create batch iterator
            batch_iterator = iter(data.DataLoader(dataset, batch_size, shuffle=True, num_workers=num_workers, collate_fn=detection_collate))
            if (epoch % 10 == 0 and epoch > 0): #or (epoch % 5 == 0 and epoch > cfg['decay1']):
                torch.save(net.state_dict(), save_folder + cfg['name']+ '_optim_'+ args.optimizer +'_epoch_' + str(epoch) + '.pth')
            epoch += 1
            loss_l, loss_c, loss_landm, loss_tot = 0, 0, 0, 0
            if epoch > 1:
                if args.optimizer != 'adamp':
                    scheduler.step() # cambia el lr
                sys.stdout.write('\n')

        load_t0 = time.time()
        #if iteration in stepvalues:
        #    step_index += 1

        #lr = adjust_learning_rate(optimizer, gamma, epoch, step_index, iteration, epoch_size)
        lr = optimizer.param_groups[0]['lr']

        # load train data
        images, targets = next(batch_iterator)
        # if num_gpu >= 1 and gpu_train:
        if gpu_train:
            images = images.cuda()
            targets = [anno.cuda() for anno in targets]
        else:
            images = images.cpu()
            targets = [anno.cpu() for anno in targets]

        # forward
        out = net(images)

        # backprop
        optimizer.zero_grad()
        #loss_l, loss_c, loss_landm = criterion(out, priors, targets)
        multiTask_loss = criterion(out, priors, targets)
        loss = cfg['loc_weight'] * multiTask_loss[0] + multiTask_loss[1] + multiTask_loss[2]
        loss.backward()
        optimizer.step()

        batch_time = time.time() - load_t0
        eta = int(batch_time * (max_iter - iteration))
        items = iteration % epoch_size + 1
        loss_l += multiTask_loss[0].item()
        loss_c += multiTask_loss[1].item()
        loss_landm += multiTask_loss[2].item()
        loss_tot += loss.item()
        #print('Epoch:{}/{} || Epochiter: {}/{} || Iter: {}/{} || Loc: {:.4f} Cla: {:.4f} Landm: {:.4f} || LR: {:.8f} || Batchtime: {:.4f} s || ETA: {}'
        #      .format(epoch, max_epoch, (iteration % epoch_size) + 1,
        #      epoch_size, iteration + 1, max_iter, loss_l.item(), loss_c.item(), loss_landm.item(), lr, batch_time, str(datetime.timedelta(seconds=eta))))
        info = f'\rEpoch:{epoch}/{max_epoch} || '
        info += f'Epochiter: {(iteration % epoch_size) + 1}/{epoch_size} || '
        info += f'Iter: {iteration + 1}/{max_iter} || '
        info += f'Loc: {loss_l/items:.3f} Cla: {loss_c/items:.3f} Landm: {loss_landm/items:.3f} Loss: {loss_tot/items:.3f}|| '
        info += f'LR: {lr:.8f} || Batchtime: {batch_time:.3f} s || ETA: {str(datetime.timedelta(seconds=eta))}'
        sys.stdout.write(info)
    torch.save(net.state_dict(), save_folder + cfg['name'] + '_optim_' + args.optimizer +'_Final.pth')


def adjust_learning_rate(optimizer, gamma, epoch, step_index, iteration, epoch_size):
    """Sets the learning rate
    # Adapted from PyTorch Imagenet example:
    # https://github.com/pytorch/examples/blob/master/imagenet/main.py
    """
    warmup_epoch = -1
    if epoch <= warmup_epoch:
        lr = 1e-6 + (initial_lr-1e-6) * iteration / (epoch_size * warmup_epoch)
    else:
        lr = initial_lr * (gamma ** (step_index))
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
    return lr

if __name__ == '__main__':
    train()
