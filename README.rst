pymodaq_plugins_lakeshore
#########################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_lakeshore.svg
   :target: https://pypi.org/project/pymodaq_plugins_lakeshore/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/Ashwolaa/pymodaq_plugins_lakeshore/actions/workflows/Test.yml/badge.svg
    :target: https://github.com/Ashwolaa/pymodaq_plugins_lakeshore/actions/workflows/Test.yml


PyMoDAQ plugin for LakeShore temperature controllers (Model 340).

Uses `pymeasure <https://pymeasure.readthedocs.io/>`_ as the hardware communication backend.


Authors
=======

* Ashwolaa


Instruments
===========

Below is the list of instruments included in this plugin

Actuators
+++++++++

* **LakeShoreController_340**: Control heater setpoints on LakeShore 340 temperature controller.
  Supports multiple output channels and input channels (A, B, C, D) for temperature readback.

Viewer0D
++++++++

* **LakeShoreController_340**: Read temperatures from selectable input channels (A, B, C, D)
  of a LakeShore 340 temperature controller. Supports kelvin, celsius, and sensor units.


Installation instructions
=========================

* PyMoDAQ >= 5.0
* Install the plugin: ``pip install pymodaq_plugins_lakeshore``
* Dependencies: ``pymeasure``, ``pyserial``
* The actuator and viewer can share the same controller via master/slave configuration.
