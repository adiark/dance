import argparse
import logging
import os
import random

import anndata
import mudata
import torch

from dance.data import Data
from dance.datasets.multimodality import ModalityPredictionDataset
from dance.modules.multi_modality.predict_modality.babel import BabelWrapper
from dance.utils import set_seed

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    OPTIMIZER_DICT = {
        "adam": torch.optim.Adam,
        "rmsprop": torch.optim.RMSprop,
    }
    rndseed = random.randint(0, 2147483647)
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--subtask", default="openproblems_bmmc_cite_phase2_rna")
    parser.add_argument("-device", "--device", default="cuda")
    parser.add_argument("-cpu", "--cpus", default=1, type=int)
    parser.add_argument("-seed", "--rnd_seed", default=rndseed, type=int)
    parser.add_argument("-m", "--model_folder", default="./models")
    parser.add_argument("--outdir", "-o", default="./logs", help="Directory to output to")
    parser.add_argument("--lossweight", type=float, default=1., help="Relative loss weight")
    parser.add_argument("--lr", "-l", type=float, default=0.01, help="Learning rate")
    parser.add_argument("--batchsize", "-b", type=int, default=64, help="Batch size")
    parser.add_argument("--hidden", type=int, default=64, help="Hidden dimensions")
    parser.add_argument("--earlystop", type=int, default=20, help="Early stopping after N epochs")
    parser.add_argument("--naive", "-n", action="store_true", help="Use a naive model instead of lego model")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max_epochs", type=int, default=500)
    args = parser.parse_args()
    args.resume = True

    torch.set_num_threads(args.cpus)
    rndseed = args.rnd_seed
    set_seed(rndseed)
    dataset = ModalityPredictionDataset(args.subtask).load_data().preprocess("feature_selection")
    device = args.device
    os.makedirs(args.model_folder, exist_ok=True)
    os.makedirs(args.outdir, exist_ok=True)

    args.outdir = os.path.abspath(args.outdir)

    if not os.path.isdir(os.path.dirname(args.outdir)):
        os.makedirs(os.path.dirname(args.outdir))

    # Specify output log file
    logger = logging.getLogger()
    fh = logging.FileHandler(f"{args.outdir}/training_{args.subtask}_{args.rnd_seed}.log", "w")
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)

    for arg in vars(args):
        logging.info(f"Parameter {arg}: {getattr(args, arg)}")

    # Construct data object
    mod1 = anndata.concat((dataset.modalities[0], dataset.modalities[2]))
    mod2 = anndata.concat((dataset.modalities[1], dataset.modalities[3]))
    mod1.var_names_make_unique()
    mod2.var_names_make_unique()
    mdata = mudata.MuData({"mod1": mod1, "mod2": mod2})
    mdata.var_names_make_unique()
    train_size = dataset.modalities[0].shape[0]
    data = Data(mdata, train_size=train_size)
    data.set_config(feature_mod="mod1", label_mod="mod2")

    # Obtain training and testing data
    x_train, y_train = data.get_train_data(return_type="torch")
    x_test, y_test = data.get_test_data(return_type="torch")

    # Train and evaluate the model
    model = BabelWrapper(args, dim_in=x_train.shape[1], dim_out=y_train.shape[1])
    model.fit(x_train, y_train, val_ratio=0.15)
    print(model.predict(x_test))
    print(model.score(x_test, y_test))
""" To reproduce BABEL on other samples, please refer to command lines belows:
GEX to ADT:
python babel.py --subtask openproblems_bmmc_cite_phase2_rna --device cuda

ADT to GEX:
python babel.py --subtask openproblems_bmmc_cite_phase2_mod2 --device cuda

GEX to ATAC:
python babel.py --subtask openproblems_bmmc_multiome_phase2_rna --device cuda

ATAC to GEX:
python babel.py --subtask openproblems_bmmc_multiome_phase2_mod2 --device cuda
"""
