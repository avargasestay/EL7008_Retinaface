# config.py

cfg_mnet = {
    'name': 'mobilenet0.25',
    'min_sizes': [[16, 32], [64, 128], [256, 512]],
    'steps': [8, 16, 32],
    'variance': [0.1, 0.2],
    'clip': False,
    'loc_weight': 2.0,
    'gpu_train': False,
    'batch_size': 32,
    'ngpu': 1,
    'epoch': 250,
    'decay1': 190,
    'decay2': 220,
    'image_size': 640,
    'pretrain': False,
    'return_layers': {'stage1': 1, 'stage2': 2, 'stage3': 3},
    'in_channel': 32,
    'out_channel': 64
}

cfg_re50 = {
    'name': 'Resnet50',
    'min_sizes': [[16, 32], [64, 128], [256, 512]],
    'steps': [8, 16, 32],
    'variance': [0.1, 0.2],
    'clip': False,
    'loc_weight': 2.0,
    'gpu_train': True,
    'batch_size': 24,
    'ngpu': 4,
    'epoch': 100,
    'decay1': 70,
    'decay2': 90,
    'image_size': 840,
    'pretrain': True,
    'return_layers': {'layer2': 1, 'layer3': 2, 'layer4': 3},
    'in_channel': 256,
    'out_channel': 256
}

cfg_efb2 = {
    'name': 'efficientb2',
    'min_sizes': [[16, 32], [64, 128], [256, 512]],
    'steps': [8, 16, 32],
    'variance': [0.1, 0.2],
    'clip': False,
    'loc_weight': 2.0,
    'gpu_train': True,
    'batch_size': 24,
    #'ngpu': 1,
    'epoch': 100,
    #'decay1': 70,
    #'decay2': 90,
    'image_size': 640,
    #'pretrain': False,
    #'return_layers': {'stage1': 1, 'stage2': 2, 'stage3': 3},
    #'in_channel': 48,
    'out_channel': 256 # porque si (por convencion y por reducir la cantidad de canales de cada stage)
}

cfg_vov39 = {
    'name': 'vovnet39b',
    'min_sizes': [[16, 32], [64, 128], [256, 512]],
    'steps': [8, 16, 32],
    'variance': [0.1, 0.2],
    'clip': False,
    'loc_weight': 2.0,
    'gpu_train': True,
    'batch_size': 32,
    #'ngpu': 1,
    'epoch': 100,
    #'decay1': 70,
    #'decay2': 90,
    'image_size': 640, # Hans recomienda usar 640 para todas
    #'pretrain': False,
    #'return_layers': {'stage1': 1, 'stage2': 2, 'stage3': 3},
    #'in_channel': 512,
    'out_channel': 256
}

