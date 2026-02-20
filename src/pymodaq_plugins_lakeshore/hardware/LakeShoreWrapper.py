import threading

from pymeasure.instruments import Instrument
from pymeasure.instruments.generic_types import SCPIUnknownMixin
from pymeasure.instruments.lakeshore.lakeshore_base import LakeShoreTemperatureChannel, \
    LakeShoreHeaterChannel
from pymeasure.instruments.validators import strict_discrete_set
import serial
from pymeasure.adapters import SerialAdapter
from serial.tools.list_ports import comports


class LockedSerialAdapter(SerialAdapter):
    """SerialAdapter with a reentrant lock to prevent concurrent serial access from multiple threads."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._comm_lock = threading.RLock()

    def ask(self, command):
        with self._comm_lock:
            return super().ask(command)

    def write(self, command):
        with self._comm_lock:
            super().write(command)

    def read(self):
        with self._comm_lock:
            return super().read()


class LakeShore340HeaterChannel(LakeShoreHeaterChannel):
    """Heater channel for the LakeShore 340, overriding the range command.

    The 340 uses a global RANGE command (no channel id) with values 0-5.
    """
    RANGE_VALUES = {'off': 0, '4 mW': 1, '40 mW': 2, '400 mW': 3, '4 W': 4, '40 W': 5}

    heater_range = Instrument.control(
        'RANGE?',
        'RANGE %i',
        """String property controlling heater range (off, 1-5).""",
        validator=strict_discrete_set,
        values=RANGE_VALUES,
        map_values=True,
    )


class LakeShore340Mixin:
    """Mixin providing shared configuration and methods for LakeShore 340 PyMoDAQ plugins.

    Intended to be used alongside DAQ_Move_base or DAQ_Viewer_base via multiple inheritance.
    """
    dict_unit = {'kelvin': 'K', 'celsius': '°C', 'sensor': 'sensor units'}
    COM_ports = [comport.name for comport in comports()]
    output_units = ['kelvin', 'celsius', 'sensor']
    input_channels = ['input_A', 'input_B', 'input_C', 'input_D']
    output_channels = ['output_1']

    params_input = [
        {'title': f'{ch}', 'name': f'{ch}', 'type': 'bool', 'value': True}
        for ch in input_channels
    ]

    params_output = [
        {'title': f'{ch}', 'name': f'{ch}', 'type': 'group', 'children': [
            {'title': f'Heater output {ch}', 'name': f'heater_output_{ch}', 'type': 'int', 'value': 0},
            {'title': f'Heater range {ch}', 'name': f'heater_range_{ch}', 'type': 'list',
             'limits': list(LakeShore340HeaterChannel.RANGE_VALUES.keys())},
            {'title': f'Heater setpoint {ch}', 'name': f'heater_setpoint_{ch}', 'type': 'float', 'value': 0},
        ]}
        for ch in output_channels
    ]

    # Per-instance flag set during remote sync to prevent echo loops and redundant hardware writes
    _is_syncing: bool = False

    def register_with_controller(self):
        """Register this plugin as an observer on the shared controller.

        Must be called after self.controller is assigned in ini_stage / ini_detector.
        """
        if hasattr(self.controller, 'register_observer'):
            self.controller.register_observer(self._sync_setting_from_remote, id(self))

    def _sync_setting_from_remote(self, param_path: tuple, value):
        """Update local settings when a sibling plugin changes a shared setting.

        Sets _is_syncing so that commit_heater_settings skips the redundant hardware
        write and the outgoing broadcast, preventing infinite echo loops.
        """
        self._is_syncing = True
        try:
            self.settings.child(*param_path).setValue(value)
        except Exception:
            pass  # param_path may not exist in this plugin (e.g. output_units location differs)
        finally:
            self._is_syncing = False

    def commit_heater_settings(self, param):
        """Apply heater-related parameter changes to the hardware and broadcast to sibling plugins.

        Parameters
        ----------
        param: Parameter
            The changed parameter.

        Returns
        -------
        bool
            True if the parameter was handled, False otherwise.
        """
        for ch in self.output_channels:
            if param.name() == f'heater_range_{ch}':
                if not self._is_syncing:
                    output_channel: LakeShore340HeaterChannel = getattr(self.controller, ch)
                    output_channel.heater_range = param.value()
                    self.controller.broadcast_setting(
                        ('output_channels', ch, f'heater_range_{ch}'),
                        param.value(), source_id=id(self))
                return True
            elif param.name() == f'heater_setpoint_{ch}':
                if not self._is_syncing:
                    # Skip redundant hardware write when apply_setpoint already did it
                    if not getattr(self, '_applying_setpoint', False):
                        output_channel: LakeShore340HeaterChannel = getattr(self.controller, ch)
                        output_channel.setpoint = param.value()
                    self.controller.broadcast_setting(
                        ('output_channels', ch, f'heater_setpoint_{ch}'),
                        param.value(), source_id=id(self))
                return True
        return False

    def close(self):
        """Terminate the communication protocol."""
        self.controller.close()


class LakeShore340Wrapper(SCPIUnknownMixin, Instrument):
    """ Represents the Lake Shore 340 Temperature Controller and provides
    a high-level interface for interacting with the instrument. Note that the
    340 provides four input channels (A, B, C, D) and two output channels (1 and 2).
    This driver makes use of the :ref:`LakeShoreChannels`.

    .. code-block:: python

        controller = LakeShore340("GPIB::1")

        print(controller.output_1.setpoint)         # Print the current setpoint for loop 1
        controller.output[1].setpoint = 50           # Change the loop 1 setpoint to 50 K
        controller.output[1].heater_range = 'low'    # Change the heater range to low.
        controller.input['A'].wait_for_temperature()   # Wait for the temperature to stabilize.
        print(controller.input['A'].temperature)       # Print the temperature at sensor A.
    """
    input_A = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'A')
    input_B = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'B')
    input_C = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'C')
    input_D = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'D')
    output_1 = Instrument.ChannelCreator(LakeShore340HeaterChannel, 1)

    def __init__(self, port, name="Lakeshore Model 340 Temperature Controller", **kwargs):
        kwargs.setdefault('read_termination', "\r\n")
        port = serial.Serial(port=port, baudrate=9600, dsrdtr=True, bytesize=serial.SEVENBITS,
                             parity=serial.PARITY_ODD, stopbits=serial.STOPBITS_ONE, timeout=1)
        adapter = LockedSerialAdapter(port, write_termination='\r\n', read_termination='\r\n')
        super().__init__(adapter, name, **kwargs)
        self._observers = []

    def register_observer(self, callback, source_id: int):
        """Register a plugin callback to be notified when a shared setting changes.

        Parameters
        ----------
        callback: callable
            Called as callback(param_path: tuple, value) when a setting changes.
        source_id: int
            id() of the registering plugin; used to exclude it from its own broadcasts.
        """
        self._observers.append((callback, source_id))

    def broadcast_setting(self, param_path: tuple, value, source_id: int = None):
        """Notify all registered observers except the source about a setting change.

        Parameters
        ----------
        param_path: tuple
            Path passed to settings.child(*param_path) on the receiving plugin.
        value:
            New value of the setting.
        source_id: int
            id() of the plugin that triggered the change; it will not receive its own broadcast.
        """
        for cb, sid in self._observers:
            if sid != source_id:
                cb(param_path, value)

    def close(self):
        self._observers.clear()
        self.adapter.close()


def main():
    my_port = 'COM4'
    controller = LakeShore340Wrapper(my_port)
    controller.close()


if __name__ == '__main__':
    main()
