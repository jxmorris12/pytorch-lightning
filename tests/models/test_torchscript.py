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

import fsspec
import pytest
import torch
from fsspec.implementations.local import LocalFileSystem

from pytorch_lightning.utilities.cloud_io import get_filesystem
from tests.helpers import BoringModel
from tests.helpers.advanced_models import BasicGAN, ParityModuleRNN
from tests.helpers.runif import RunIf


@pytest.mark.parametrize("modelclass", [BoringModel, ParityModuleRNN, BasicGAN])
def test_torchscript_input_output(modelclass):
    """Test that scripted LightningModule forward works."""
    model = modelclass()

    if isinstance(model, BoringModel):
        model.example_input_array = torch.randn(5, 32)

    script = model.to_torchscript()
    assert isinstance(script, torch.jit.ScriptModule)

    model.eval()
    with torch.no_grad():
        model_output = model(model.example_input_array)

    script_output = script(model.example_input_array)
    assert torch.allclose(script_output, model_output)


@pytest.mark.parametrize("modelclass", [BoringModel, ParityModuleRNN, BasicGAN])
def test_torchscript_example_input_output_trace(modelclass):
    """Test that traced LightningModule forward works with example_input_array."""
    model = modelclass()

    if isinstance(model, BoringModel):
        model.example_input_array = torch.randn(5, 32)

    script = model.to_torchscript(method="trace")
    assert isinstance(script, torch.jit.ScriptModule)

    model.eval()
    with torch.no_grad():
        model_output = model(model.example_input_array)

    script_output = script(model.example_input_array)
    assert torch.allclose(script_output, model_output)


def test_torchscript_input_output_trace():
    """Test that traced LightningModule forward works with example_inputs."""
    model = BoringModel()
    example_inputs = torch.randn(1, 32)
    script = model.to_torchscript(example_inputs=example_inputs, method="trace")
    assert isinstance(script, torch.jit.ScriptModule)

    model.eval()
    with torch.no_grad():
        model_output = model(example_inputs)

    script_output = script(example_inputs)
    assert torch.allclose(script_output, model_output)


@RunIf(min_cuda_gpus=1)
@pytest.mark.parametrize("device", [torch.device("cpu"), torch.device("cuda", 0)])
def test_torchscript_device(device):
    """Test that scripted module is on the correct device."""
    model = BoringModel().to(device)
    model.example_input_array = torch.randn(5, 32)

    script = model.to_torchscript()
    assert next(script.parameters()).device == device
    script_output = script(model.example_input_array.to(device))
    assert script_output.device == device


def test_torchscript_retain_training_state():
    """Test that torchscript export does not alter the training mode of original model."""
    model = BoringModel()
    model.train(True)
    script = model.to_torchscript()
    assert model.training
    assert not script.training
    model.train(False)
    _ = model.to_torchscript()
    assert not model.training
    assert not script.training


@pytest.mark.parametrize("modelclass", [BoringModel, ParityModuleRNN, BasicGAN])
def test_torchscript_properties(modelclass):
    """Test that scripted LightningModule has unnecessary methods removed."""
    model = modelclass()
    script = model.to_torchscript()
    assert not hasattr(model, "batch_size") or hasattr(script, "batch_size")
    assert not hasattr(model, "learning_rate") or hasattr(script, "learning_rate")
    assert not callable(getattr(script, "training_step", None))


@pytest.mark.parametrize("modelclass", [BoringModel, ParityModuleRNN, BasicGAN])
def test_torchscript_save_load(tmpdir, modelclass):
    """Test that scripted LightningModule is correctly saved and can be loaded."""
    model = modelclass()
    output_file = str(tmpdir / "model.pt")
    script = model.to_torchscript(file_path=output_file)
    loaded_script = torch.jit.load(output_file)
    assert torch.allclose(next(script.parameters()), next(loaded_script.parameters()))


@pytest.mark.parametrize("modelclass", [BoringModel, ParityModuleRNN, BasicGAN])
def test_torchscript_save_load_custom_filesystem(tmpdir, modelclass):
    """Test that scripted LightningModule is correctly saved and can be loaded with custom filesystems."""

    _DUMMY_PRFEIX = "dummy"
    _PREFIX_SEPARATOR = "://"

    class DummyFileSystem(LocalFileSystem):
        ...

    fsspec.register_implementation(_DUMMY_PRFEIX, DummyFileSystem, clobber=True)

    model = modelclass()
    output_file = os.path.join(_DUMMY_PRFEIX, _PREFIX_SEPARATOR, tmpdir, "model.pt")
    script = model.to_torchscript(file_path=output_file)

    fs = get_filesystem(output_file)
    with fs.open(output_file, "rb") as f:
        loaded_script = torch.jit.load(f)

    assert torch.allclose(next(script.parameters()), next(loaded_script.parameters()))


def test_torchcript_invalid_method(tmpdir):
    """Test that an error is thrown with invalid torchscript method."""
    model = BoringModel()
    model.train(True)

    with pytest.raises(ValueError, match="only supports 'script' or 'trace'"):
        model.to_torchscript(method="temp")


def test_torchscript_with_no_input(tmpdir):
    """Test that an error is thrown when there is no input tensor."""
    model = BoringModel()
    model.example_input_array = None

    with pytest.raises(ValueError, match="requires either `example_inputs` or `model.example_input_array`"):
        model.to_torchscript(method="trace")
