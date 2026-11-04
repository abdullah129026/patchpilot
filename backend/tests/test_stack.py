from app.stack import detect


def test_python_manifest_wins():
    assert detect(["pyproject.toml", "main.js"]) == "python"


def test_python_requirements():
    assert detect(["requirements.txt", "app.py"]) == "python"


def test_python_by_extension_majority():
    assert detect(["a.py", "b.py", "README.md"]) == "python"


def test_javascript_manifest():
    assert detect(["package.json", "index.js", "README.md"]) == "javascript"


def test_cpp_cmake():
    assert detect(["CMakeLists.txt", "main.cpp", "util.h"]) == "cpp"


def test_cpp_by_extension():
    assert detect(["main.cc", "lib.hpp"]) == "cpp"


def test_unknown_returns_none():
    assert detect(["README.md", "notes.txt"]) is None
    assert detect([]) is None
