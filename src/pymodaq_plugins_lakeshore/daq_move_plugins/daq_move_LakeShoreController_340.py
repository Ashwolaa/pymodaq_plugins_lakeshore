from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main, DataActuatorType,\
    DataActuator
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter
from pymeasure.instruments.lakeshore.lakeshore_base import LakeShoreTemperatureChannel, \
    LakeShoreHeaterChannel
from pymodaq_plugins_lakeshore.hardware.LakeShoreWrapper import LakeShore340Wrapper, LakeShore340Mixin


class DAQ_Move_LakeShoreController_340(LakeShore340Mixin, DAQ_Move_base):
    """ Instrument plugin class for controlling a LakeShore 340 temperature controller.

    Uses the heater outputs to set temperature and reads from input channels.
    Can share the controller with DAQ_0DViewer_LakeShoreController_340 via master/slave.

    Attributes:
    -----------
    controller: LakeShore340Wrapper
        The wrapper around the LakeShore 340 hardware.
    """
    _controller_units = 'K'
    is_multiaxes = True
    _axis_names = LakeShore340Mixin.input_channels
    _epsilon = 0.05
    data_actuator_type = DataActuatorType['DataActuator']

    params = [
        {'title': 'Controller Status:', 'name': 'controller_status', 'type': 'list',
         'value': 'Master', 'limits': ['Master', 'Slave']},
        {'title': 'COM:', 'name': 'com_port', 'type': 'list',
         'limits': LakeShore340Mixin.COM_ports},
        {'title': 'Output channels:', 'name': 'output_channels', 'type': 'group', 'children':
         [{'title': 'Output units', 'name': 'output_units', 'type': 'list',
           'limits': LakeShore340Mixin.output_units}]
         + LakeShore340Mixin.params_output},
        {'title': 'Home temperature', 'name': 'home_temperature', 'type': 'float', 'value': 30},
    ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.controller: LakeShore340Wrapper = None

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        input_channel: LakeShoreTemperatureChannel = getattr(self.controller, self.axis_name)
        value = getattr(input_channel, self.settings.child('output_channels', 'output_units').value())
        pos = DataActuator(data=value)
        pos = self.get_position_with_scaling(pos)
        return pos

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == "output_units":
            self.settings.child('units').setValue(self.dict_unit[param.value()])
        else:
            self.commit_heater_settings(param)

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        if self.settings.child('controller_status').value() == "Slave":
            new_controller = None
        else:
            new_controller = LakeShore340Wrapper(port=self.settings.child('com_port').value())

        self.controller = self.ini_stage_init(old_controller=controller,
                                              new_controller=new_controller)

        info = "LakeShore 340 Temperature Controller"
        initialized = bool(self.controller.ask('*IDN?'))
        return info, initialized

    def apply_setpoint(self, value: DataActuator):
        """ Apply the setpoint to each output channel

        Parameters
        ----------
        value: (float) value of the setpoint
        """
        for ch in self.output_channels:
            output_channel: LakeShoreHeaterChannel = getattr(self.controller, ch)
            output_channel.setpoint = value.value()
            self.settings.child('output_channels', ch, f'heater_setpoint_{ch}').setValue(value.value())

    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """
        value = self.check_bound(value)
        self.target_value = value
        value = self.set_position_with_scaling(value)
        self.apply_setpoint(value)

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)
        self.apply_setpoint(value)

    def move_home(self):
        """Call the reference method of the controller"""
        self.move_abs(self.settings.child('home_temperature').value())

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        self.move_abs(self.get_actuator_value())


if __name__ == '__main__':
    main(__file__, init=False)
