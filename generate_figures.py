# Script for data and figure generation for Occam's Quantum Strop

import os
import subprocess

"""
# Make tikz figures of eMs
#######################

# PC
####
os.chdir("figures_and_code/perturbed_coin/eM")

# I use other flags in my TexShop, but only --shell-escape appears to be necessary here
#subprocess.call(["pdflatex", "--file-line-error", "--synctex=1", "--shell-escape", "perturbed_coin.tex"])

subprocess.call(["pdflatex", "--shell-escape", "perturbed_coin.tex"])

os.chdir("../../..")

# RkGM
####
os.chdir("figures_and_code/RkGM/eM")

subprocess.call(["pdflatex", "--shell-escape", "RkGM.tex"])

os.chdir("../../..")

# nemo
####
os.chdir("figures_and_code/nemo/eM")

subprocess.call(["pdflatex", "--shell-escape", "nemo.tex"])

os.chdir("../../..")
"""


"""
# Compute Cq(L) curves
#######################

# PC
####
os.chdir("figures_and_code/perturbed_coin/python")

subprocess.call(["python", "perturbed_coin.py"])

os.chdir("../../..")

# RkGM
####
os.chdir("figures_and_code/RkGM/python")

subprocess.call(["python", "RkGM.py"])

os.chdir("../../..")

# nemo
####
os.chdir("figures_and_code/nemo/python")

subprocess.call(["python", "nemo.py"])

os.chdir("../../..")
"""

"""
# Make composite figures using eMs and Cq(L) curves
# Convert to eps for Scientific Reports
#######################

# PC
####
os.chdir("figures_and_code/perturbed_coin/composite")

subprocess.call(["pdflatex", "--shell-escape", "multi_fig_w_tikz.tex"])
subprocess.call(["pdftops", "-eps", "multi_fig_w_tikz.pdf"])

os.chdir("../../..")

# RkGM
####
os.chdir("figures_and_code/RkGM/composite")

subprocess.call(["pdflatex", "--shell-escape", "multi_fig_w_tikz.tex"])
subprocess.call(["pdftops", "-eps", "multi_fig_w_tikz.pdf"])

os.chdir("../../..")

# nemo
####
os.chdir("figures_and_code/nemo/composite")

subprocess.call(["pdflatex", "--shell-escape", "multi_fig_w_tikz.tex"])
subprocess.call(["pdftops", "-eps", "multi_fig_w_tikz.pdf"])

os.chdir("../../..")
"""

"""
# Convert existing pdfs to eps
#######################

os.chdir("figures_and_code/img")

subprocess.call(["pdftops", "-eps", "R_vs_k_6.pdf"])

os.chdir("../../..")
"""

"""
# Make prediction generation tradeoff fig
# Convert to eps
#######################

os.chdir("figures_and_code/prediction_generation_tradeoff")

subprocess.call(["pdflatex", "--shell-escape", "prediction_generation_tradeoff.tex"])
subprocess.call(["pdftops", "-eps", "prediction_generation_tradeoff.pdf"])

os.chdir("../../..")
"""


"""
# Make pairwise merger machines
#######################

# PC
####
os.chdir("figures_and_code/PMM/perturbed_coin")

subprocess.call(["pdflatex", "--shell-escape", "perturbed_coin_PMM.tex"])

os.chdir("../../..")

# RkGM
####
os.chdir("figures_and_code/PMM/RkGM")

subprocess.call(["pdflatex", "--shell-escape", "RkGM_PMM.tex"])

os.chdir("../../..")

# nemo
####
os.chdir("figures_and_code/PMM/nemo")

subprocess.call(["pdflatex", "--shell-escape", "nemo_PMM.tex"])

os.chdir("../../..")
"""

"""
# Make composite figure of pairwise merger machines
# Convert to eps
#######################

# composite
####
os.chdir("figures_and_code/PMM/composite")

subprocess.call(["pdflatex", "--shell-escape", "multi_fig_w_tikz.tex"])
subprocess.call(["pdftops", "-eps", "multi_fig_w_tikz.pdf"])

os.chdir("../../..")
"""