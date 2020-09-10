#!/bin/bash
set -Eeuo pipefail


# Define help message
show_help() {
    echo """
    Commands
    ----------------------------------------------------------------------------
    bash          : run bash
    build         : build python wheel of library in /dist
    eval          : eval shell command
    pip_freeze    : freeze pip dependencies and write to requirements.txt
    start         : run application
    test_unit     : run tests
    test_lint     : run flake8 tests
    test_coverage : run tests with coverage output

    """
}

PYTEST="pytest --cov-report term-missing --cov=app --cov-append -p no:cacheprovider"
# --cov=app --cov-append -p no:cacheprovider

test_flake8() {
    flake8 /test/. --config=/test/setup.cfg
}

test() {
    $PYTEST -m $1
    rm -R .pytest_cache || true
    rm -rf tests/__pycache__ || true
}

test_all() {
    $PYTEST
    rm -R .pytest_cache || true
    rm -rf tests/__pycache__ || true
}

run_local() {
    export FLASK_APP=app.local_server
    flask run --host=0.0.0.0 --port=9009
}

case "$1" in
    bash )
        bash
    ;;

    eval )
        eval "${@:2}"
    ;;


    pip_freeze )

        rm -rf /tmp/env
        pip3 install -r ./conf/pip/primary-requirements.txt --upgrade

        cat /code/conf/pip/requirements_header.txt | tee conf/pip/requirements.txt
        pip freeze --local | grep -v appdir | tee -a conf/pip/requirements.txt
    ;;

    start )
        test_flake8
        run_local
    ;;

    test)
        test_flake8
        test "${@:2}"
    ;;

    test_all)
        test_flake8
        test_all
    ;;

    test_lint)
        test_flake8
    ;;

    build)
        # remove previous build if needed
        rm -rf dist
        rm -rf build
        rm -rf .eggs
        # create the distribution
        python setup.py bdist_wheel --universal

        # remove useless content
        rm -rf build
    ;;

    help)
        show_help
    ;;

    *)
        show_help
    ;;
esac

echo $1