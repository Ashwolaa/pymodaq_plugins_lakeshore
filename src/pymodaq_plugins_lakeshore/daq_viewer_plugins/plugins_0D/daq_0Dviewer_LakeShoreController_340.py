import numpy as np

from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins
from pymeasure.instruments.lakeshore.lakeshore_base import LakeShoreTemperatureChannel
from pymodaq_plugins_lakeshore.hardware.LakeShoreWrapper import LakeShore340Wrapper, LakeShore340Mixin


class DAQ_0DViewer_LakeShoreController_340(LakeShore340Mixin, DAQ_Viewer_base):
    """ Instrument plugin class for reading temperatures from a LakeShore 340 controller.

    Reads temperature from selected input channels (A, B, C, D) and exposes
    heater output settings. Can share the controller with DAQ_Move_LakeShoreController_340
    via master/slave.

    Attributes:
    -----------
    controller: LakeShore340Wrapper
        The wrapper around the LakeShore 340 hardware.
    """
    params = comon_parameters + [
        {'title': 'COM:', 'name': 'com_port', 'type': 'list',
         'limits': LakeShore340Mixin.COM_ports},
        {'title': 'Output units', 'name': 'output_units', 'type': 'list',
         'limits': LakeShore340Mixin.output_units},
        {'title': 'Input channels:', 'name': 'input_channels', 'type': 'group',
         'children': LakeShore340Mixin.params_input},
        {'title': 'Output channels:', 'name': 'output_channels', 'type': 'group',
         'children': LakeShore340Mixin.params_output},
    ]

    def ini_attributes(self):
        self.controller: LakeShore340Wrapper = None

    def get_active_input_channels(self):
        """Return the list of input channels whose checkbox is enabled."""
        return [ch for ch in self.input_channels
                if self.settings.child('input_channels', ch).value()]

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        self.commit_heater_settings(param)

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        self.ini_detector_init(slave_controller=controller)

        if self.is_master:
            self.controller = LakeShore340Wrapper(port=self.settings.child('com_port').value())

        active_channels = self.get_active_input_channels()
        self.dte_signal_temp.emit(DataToExport(
            name='LakeShore340',
            data=[DataFromPlugins(
                name='Temperatures',
                data=[np.array([0.0]) for _ in active_channels],
                dim='Data0D',
                labels=active_channels,
            )]
        ))

        info = "LakeShore 340 Temperature Controller"
        initialized = bool(self.controller.ask('*IDN?'))
        return info, initialized

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging
        kwargs: dict
            others optionals arguments
        """
        unit = self.settings.child('output_units').value()
        active_channels = self.get_active_input_channels()
        data_channels = []
        for ch in active_channels:
            input_channel: LakeShoreTemperatureChannel = self.controller.inputs[ch]
            value = getattr(input_channel, unit)
            data_channels.append(np.array([value]))

        self.dte_signal.emit(DataToExport(
            name='LakeShore340',
            data=[DataFromPlugins(
                name='Temperatures',
                data=data_channels,
                dim='Data0D',
                labels=active_channels,
            )]
        ))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        return ''


if __name__ == '__main__':
    main(__file__)
