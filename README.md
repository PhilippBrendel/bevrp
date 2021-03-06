<!--
*** Thanks for checking out this README Template. If you have a suggestion that would
*** make this better, please fork the repo and create a pull request or simply open
*** an issue with the tag "enhancement".
*** Thanks again! Now go create something AMAZING! :D
-->





<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/PhilippBrendel/bevrp">
    <img src="images/smart_krit.jpg" alt="Logo" width="100" height="80">
  </a>

  <h3 align="center">BEVRP</h3>

  <p align="center">
    The Bidirectional Vehicle Routing Problem
    <br />
    <a href="https://github.com/PhilippBrendel/bevrp"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/PhilippBrendel/bevrp">View Demo</a>
    ·
    <a href="https://github.com/PhilippBrendel/bevrp/issues">Report Bug</a>
    ·
    <a href="https://github.com/PhilippBrendel/bevrp/issues">Request Feature</a>
  </p>
</p>



<!-- TABLE OF CONTENTS -->
## Table of Contents

* [About the Project](#about-the-project)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Setup](#setup)
* [Usage](#usage)
  * [Configuration](#configuration)
  * [Optimization](#optimization)
  * [Visualization](#visualization)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)
* [Acknowledgements](#acknowledgements)



<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](https://example.com)

This project includes code to solve the Bi-directional electric vehicle routing problem (B-EVRP).

### Included

* [smart_krit.py](https://github.com/PhilippBrendel/bevrp/blob/main/smart_krit.py): direct solver of BEVRP
* [greedy.py](https://github.com/PhilippBrendel/bevrp/blob/main/greedy.py): implementation of Greedy-2 heuristic
* [visualizers.py](https://github.com/PhilippBrendel/bevrp/blob/main/visualizers.py): visualization tools
* [gui.py](https://github.com/PhilippBrendel/bevrp/blob/main/gui.py): Simple GUI for visualization functionalities 
* [utils.py](https://github.com/PhilippBrendel/bevrp/blob/main/utils.py): various helper functions
* [pypeline.py](https://github.com/PhilippBrendel/bevrp/blob/main/pypeline.py): automatization script for sequential solving of multiple instances via many config-files 
* [config.yaml](https://github.com/PhilippBrendel/bevrp/blob/main/config.yaml): examplary config-file
* [data](https://github.com/PhilippBrendel/bevrp/blob/main/data): examplary data containing energy consumers, producers and vehicles from Kaiserslautern
* [showroom](https://github.com/PhilippBrendel/bevrp/blob/main/showroom): A selection of solution instances that can be viewed right away



<!-- GETTING STARTED -->
## Getting Started

To Use the code you require a license for the Gurobi optimization software as well as a Python distribution such as Anaconda.

### Prerequisites

* [Gurobi licence](https://www.gurobi.com/)

* [Anaconda](https://www.anaconda.com/)


### Setup

<!-- 1. Get a free API Key at [https://example.com](https://example.com) -->
1. Clone the repo
```sh
git clone https://github.com/PhilippBrendel/bevrp.git
```
2. Create Conda environmemt via provided YAML-file
```sh
conda env create -f conda_env.yaml
```
3. Activate Conda environmemt
```sh
conda activate bevrp
```
4. Install Gurobi licence
```sh
grbgetkey xxxxxxxx-xxxx...
```


<!-- USAGE EXAMPLES -->
## Usage

### Configuration

Configure YAML-file for your problem. 
Default file used is *bevrp/config.yaml* if not specified otherwise via cmd-line option (see below).

### Optimization

Direct solver:
```sh
python smart_krit.py -c my_sk_config.yaml
```

Greedy-2 heuristic:
```sh
python greedy2.py -c my_greedy_config.yaml
```

_For more examples, please refer to the [TODO](https://example.com)_


### Visualization

The included visualization tools are executed by specifying the path to the desired solution files - both the .txt and .p need to exist at the same location:
```
python visualizers.py -n /path/to/my/results/name_of_the_instance
```

There is also a simple GUI provided that is called via:
```sh
python gui.py
```

1. Choose the directory that contains your result files (e.g. *my_results.p* and *my_results.txt*)
2. Select the respective solution files from the file-list
3. The Solutions will be visualized automatically


<!-- ROADMAP -->
## Roadmap

See the [open issues](https://github.com/PhilippBrendel/bevrp/issues) for a list of proposed features (and known issues).



<!-- CONTRIBUTING -->
## Contributing
TODO
Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- LICENSE -->
## License

TODO. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact

Philipp Brendel - philipp.brendel@iisb.fraunhofer.de - philipp.brendel@fau.de

Project Link: [https://github.com/PhilippBrendel/bevrp](https://github.com/PhilippBrendel/bevrp)



<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements
* [Gurobi](https://www.gurobi.com/)
* [Anaconda](https://www.anaconda.com/)
* [Conda Cheat Sheet](https://docs.conda.io/projects/conda/en/4.6.0/_downloads/52a95608c49671267e40c689e0bc00ca/conda-cheatsheet.pdf)
* [PySimpleGUI](https://pypi.org/project/PySimpleGUI/)




<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/philippbrendel/bevrp.svg?style=flat-square
[contributors-url]: https://github.com/philippbrendel/bevrp/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/philippbrendel/bevrp.svg?style=flat-square
[forks-url]: https://github.com/philippbrendel/bevrp/network/members
[stars-shield]: https://img.shields.io/github/stars/philippbrendel/bevrp.svg?style=flat-square
[stars-url]: https://github.com/philippbrendel/bevrp/stargazers
[issues-shield]: https://img.shields.io/github/issues/philippbrendel/bevrp.svg?style=flat-square
[issues-url]: https://github.com/philippbrendel/bevrp/issues
[license-shield]: https://img.shields.io/github/license/philippbrendel/bevrp.svg?style=flat-square
[license-url]: https://github.com/philippbrendel/bevrp/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/philipp-brendel-9059171a6/
[product-screenshot]: images/smart_krit.jpg