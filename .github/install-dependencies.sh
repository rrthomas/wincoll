#!/bin/sh

# Ubuntu
if [ "$RUNNER_OS" = "Linux" ]; then
    sudo apt-get -y install python3-build python3-venv python3-pygame python3-importlib-resources make
    pip install --user pyscroll pytmx
fi

# macOS
if [ "$RUNNER_OS" = "macOS" ]; then
    brew install tox
    # Prepend optional brew binary directories to PATH
    echo "$(brew --prefix)/opt/python/libexec/bin" >> $GITHUB_PATH
    pip install --user --break-system-packages build pygame importlib-resources typing-extensions platformdirs pyscroll pytmx
    # Prepend user bin directory to PATH
    echo $(python -c "import os; import sysconfig; print(sysconfig.get_path('scripts', f'{os.name}_user'))") >> $GITHUB_PATH
fi
