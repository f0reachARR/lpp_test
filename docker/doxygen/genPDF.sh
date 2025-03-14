#!/bin/bash
doxygen /doxygen/Doxyfile
cd latex
make pdf
cp refman.pdf ../spec.pdf
cd ..
rm -rf latex