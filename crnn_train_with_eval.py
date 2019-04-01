from keras import backend as K
from keras.optimizers import Adadelta
from keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard
from data_process import DataProcess
from data_generator import DataGenerator
import Model as crnn_model
import parameter as params
import os
import numpy as np
import itertools
import tensorflow as tf
from batch_test import epoch_eval


#K.set_learning_phase(0)


def data_preprocess():
    # check train_data
    if os.path.exists(os.path.exists(params.cut_img_save_path)) and \
            os.path.exists(params.json_train_path) and \
            os.path.exists(params.json_val_path) and \
            os.path.exists(params.generate_key_path):
        print("train_data have been build, pre process task over !")
        return
    else:
        print("train_data not exist, do processing...")
        data_proc = DataProcess()
        data_proc.data_preprocess()


def load_train_and_val_data():
    # train data path
    json_train_path = params.json_train_path
    json_val_path = params.json_val_path
    cut_img_save_path = params.cut_img_save_path
    key_path = params.char_path

    # data generator
    train_data = DataGenerator(img_dirpath=cut_img_save_path,
                               json_path=json_train_path,
                               char_path=key_path,
                               img_w=params.img_w,
                               img_h=params.img_h,
                               batch_size=params.batch_size,
                               downsample_factor=params.downsample_factor,
                               max_text_len=params.max_text_len)
    train_data.build_data()
    train_sample_num = train_data.n

    val_data = DataGenerator(img_dirpath=cut_img_save_path,
                             json_path=json_val_path,
                             char_path=key_path,
                             img_w=params.img_w,
                             img_h=params.img_h,
                             batch_size=params.batch_size,
                             downsample_factor=params.downsample_factor,
                             max_text_len=params.max_text_len)
    val_data.build_data()
    val_sample_num = val_data.n

    return train_data.next_batch(), \
           val_data.next_batch(), \
           train_sample_num, \
           val_sample_num



def train_model():
    # calc num_classes
    key_f = open(params.char_path, 'r', encoding='utf-8')
    chars = key_f.read()
    key_f.close()
    params.num_classes = len(chars) + 1
    print('params.num_classes: ', params.num_classes)

    model = crnn_model.get_Model(training=True)
    try:
        latest_weights = params.load_weights_path
        print("find latest_weights exists.", latest_weights)
        if latest_weights != None:
            model.load_weights(latest_weights)
            print("...load exist weights: ", latest_weights)
        else:
            print("history weights file not exist, train a new one.")
    except Exception as e:
        print('warn: ',str(e))
        print("historical weights data can not be used, train a new one...")
        pass

    train_data_gen, val_data_gen, train_sample_num, val_sample_num = load_train_and_val_data()

    ada = Adadelta()

    early_stop = EarlyStopping(monitor='val_loss',
                               min_delta=0.001,
                               patience=8,
                               mode='min',
                               verbose=1)
    checkpoint = ModelCheckpoint(filepath='/data/output/CRNN--{epoch:02d}--{val_loss:.3f}.h5',
                                 monitor='val_loss',
                                 save_best_only=False,
                                 save_weights_only=True,
                                 verbose=1,
                                 mode='min',
                                 period=1)
    tensor_board = TensorBoard(log_dir='/data/output')
    # the loss calc occurs elsewhere, so use a dummy lambda func for the loss
    model.compile(loss={'ctc': lambda y_true, y_pred: y_pred}, optimizer=ada)

    # captures output of softmax so we can decode the output during visualization

    batch_size = params.batch_size
    epoch_num = params.epoch_num
    val_batch_size = params.val_batch_size

    for ep_i in range(epoch_num):
        print("epoch: ", ep_i+1)
        model.fit_generator(generator=train_data_gen,
                            steps_per_epoch=train_sample_num // batch_size,
                            epochs=ep_i+1,
                            callbacks=[],
                            verbose=1,
                            initial_epoch=ep_i,
                            validation_data=val_data_gen,
                            validation_steps=val_sample_num // val_batch_size)

        curr_weights_path = "/data/output/crnn_ticket_20190327/crnn_weights_d10w_ticket_id_date_20190327_ep_%d.h5"%(ep_i+1)
        model.save_weights(curr_weights_path)
        train_data_acc = epoch_eval.eval_on_generating_data(curr_weights_path)
        print(" -- train_data_acc: ", train_data_acc)
        real_data_acc, detail_info = epoch_eval.eval_on_real_data(curr_weights_path)
        print(" -- real_data_acc: ", real_data_acc, detail_info)




if __name__ == "__main__":
    data_preprocess()
    train_model()
