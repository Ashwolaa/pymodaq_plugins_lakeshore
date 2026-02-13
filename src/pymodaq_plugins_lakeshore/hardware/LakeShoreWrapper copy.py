from pymeasure.instruments import Instrument
from pymeasure.instruments.generic_types import SCPIUnknownMixin
from pymeasure.instruments.lakeshore.lakeshore_base import LakeShoreTemperatureChannel, \
    LakeShoreHeaterChannel
import serial
from pymeasure.adapters import SerialAdapter


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
    inputs = {f"input_{ch}": Instrument.ChannelCreator(LakeShoreTemperatureChannel, f'{ch}')  for ch in ['A','B','C','D']}
    outputs = {f"output_{ch}": Instrument.ChannelCreator(LakeShoreHeaterChannel, f'{ch}')  for ch in [1,2]}    
    # input_A = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'A')
    # input_B = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'B')
    # input_C = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'C')
    # input_D = Instrument.ChannelCreator(LakeShoreTemperatureChannel, 'D')
    # output_1 = Instrument.ChannelCreator(LakeShoreHeaterChannel, 1)
    # output_2 = Instrument.ChannelCreator(LakeShoreHeaterChannel, 2)

    def __init__(self, port, name="Lakeshore Model 340 Temperature Controller", **kwargs):
        kwargs.setdefault('read_termination', "\r\n")
        port = serial.Serial(port=port, baudrate=9600, dsrdtr=True, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, stopbits=serial.STOPBITS_ONE, timeout=1, )
        adapter = SerialAdapter(port,write_termination='\r\n',read_termination='\r\n',)   
        super().__init__(
            adapter,
            name,
            **kwargs
        )
    def close(self,):
        # Close connection
        self.adapter.close()

def main():
    L = LakeShore340Wrapper('COM4')


if __name__ == '__main__':
    main()