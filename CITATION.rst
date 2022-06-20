If you use ASDF for work/research presented in a publication (whether directly,
as a dependency to another package), please cite the Zenodo DOI for the appropriate
version of ASDF.  The versions (and their BibTeX entries) can be found at:

.. only:: html

    .. include:: ../../README.rst
        :start-after: begin-zenodo:
        :end-before: end-zenodo:

.. only:: latex

    .. admonition:: Zenodo DOI

        https://zenodo.org/badge/latestdoi/18112754

We also recommend and encourage you to cite the general ASDF paper:

.. code:: bibtex

    @article{GREENFIELD2015240,
    title = {ASDF: A new data format for astronomy},
    journal = {Astronomy and Computing},
    volume = {12},
    pages = {240-251},
    year = {2015},
    issn = {2213-1337},
    doi = {https://doi.org/10.1016/j.ascom.2015.06.004},
    url = {https://www.sciencedirect.com/science/article/pii/S2213133715000645},
    author = {P. Greenfield and M. Droettboom and E. Bray},
    keywords = {FITS, File formats, Standards, World coordinate system},
    abstract = {We present the case for developing a successor format for the immensely successful FITS format. We first review existing alternative formats and discuss why we do not believe they provide an adequate solution. The proposed format is called the Advanced Scientific Data Format (ASDF) and is based on an existing text format, YAML, that we believe removes most of the current problems with the FITS format. An overview of the capabilities of the new format is given along with specific examples. This format has the advantage that it does not limit the size of attribute names (akin to FITS keyword names) nor place restrictions on the size or type of values attributes have. Hierarchical relationships are explicit in the syntax and require no special conventions. Finally, it is capable of storing binary data within the file in its binary form. At its basic level, the format proposed has much greater applicability than for just astronomical data.}
    }
