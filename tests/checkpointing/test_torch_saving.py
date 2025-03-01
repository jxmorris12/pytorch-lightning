# Copyright The PyTorch Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

import torch

from pytorch_lightning import Trainer
from tests.helpers import BoringModel
from tests.helpers.runif import RunIf


def test_model_torch_save(tmpdir):
    """Test to ensure torch save does not fail for model and trainer."""
    model = BoringModel()
    num_epochs = 1
    trainer = Trainer(default_root_dir=tmpdir, max_epochs=num_epochs)
    temp_path = os.path.join(tmpdir, "temp.pt")
    trainer.fit(model)

    # Ensure these do not fail
    torch.save(trainer.model, temp_path)
    torch.save(trainer, temp_path)
    trainer = torch.load(temp_path)


@RunIf(skip_windows=True)
def test_model_torch_save_ddp_cpu(tmpdir):
    """Test to ensure torch save does not fail for model and trainer using cpu ddp."""
    model = BoringModel()
    num_epochs = 1
    trainer = Trainer(
        default_root_dir=tmpdir, max_epochs=num_epochs, strategy="ddp_spawn", accelerator="cpu", devices=2, logger=False
    )
    temp_path = os.path.join(tmpdir, "temp.pt")
    trainer.fit(model)

    # Ensure these do not fail
    torch.save(trainer.model, temp_path)
    torch.save(trainer, temp_path)


@RunIf(min_cuda_gpus=2)
def test_model_torch_save_ddp_cuda(tmpdir):
    """Test to ensure torch save does not fail for model and trainer using gpu ddp."""
    model = BoringModel()
    num_epochs = 1
    trainer = Trainer(
        default_root_dir=tmpdir, max_epochs=num_epochs, strategy="ddp_spawn", accelerator="gpu", devices=2
    )
    temp_path = os.path.join(tmpdir, "temp.pt")
    trainer.fit(model)

    # Ensure these do not fail
    torch.save(trainer.model, temp_path)
    torch.save(trainer, temp_path)
