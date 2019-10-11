# MBE Toolbox

In the [Laboratory of Semiconductor Materials](https://www.epfl.ch/labs/lmsc/) at [EPFL](https://www.epfl.ch) we do [Molecular beam epitaxy (MBE)](https://en.wikipedia.org/wiki/Molecular-beam_epitaxy) of III-V semiconductor nanomaterials. We use our big, expensive MBE cluster to grow ultra-pure nano-scale crystals ranging from vertical nanowires to horizontal nanomembranes and everything in between.

Sadly, MBE growth is hard. Growth recipes can become quite complex and often include flux calibrations, layer thickness calculations, unit conversions etc. Because of this complexity, I decided to build my own recipe launcher from scratch in Python. This is the **MBE Toolbox**.

With the flexibility of Python, there were a few things that I could do that made life a bit easier, including:

 - **Calibration Class**: Automatic integration of beam flux calibrations.
 - **Virtual MBE**: Test your new recipes virtually before running them on precious samples.
 - **Valve Guardian**: Protect those expensive Group V valves during emergencies.
 - **Pyrometer Feedback**: Make fine temperature adjustments based on pyrometer readings.

## Core
The core of this software is provided by the MBERecipe class located in in the recipe_helper.py. At the start of each recipe we need to create an MBERecipe object. All interaction with the MBE is then performed through this object. For example:

    from recipe_helper import MBERecipe
    with MBERecipe as mbe:
	    ...
	    mbe.start_recipe()
	    mbe.set_param("AsCracker.Valve.OP", as_valve_gaas)
	    mbe.shutter("As", True)
	    mbe.waiting(60 * 3) # Wait 3 min
	    ...
The advantage of using a "with" statement is that we can specify how to treat the error by using the `__exit__()` function of the MBERecipe class to make the script exits gracefully (closes open connections, potentially cools down cells, etc.).  In the future, one could also think of sending an alert to the grower in the case of an unexpected abort of the script.

## Calibrations Class
One of the main motivations to write a recipe environment in Python is being able to integrate calibrations automatically into a recipe. The reasoning being that the grower doesn't care about cell temperature, all they care about is the flux (ie: deposition rate). Setting the proper cell temperature is something that can (and should) be handled in the background by the recipe environment. 

The Calibration class is therefore a class which can auto-load the latest calibration file for a given cell and convert a specified material flux into a cell set temperature. This kind of implementation has the added benefit of simplifying recipes and allowing for them to be easily compared because set temperatures were not hard-coded.

    from mbe_calibration import Calibration
    ...
    # Create a calibration object for each cell
    calib_In = Calibration("In")
    calib_Ga = Calibration("Ga", rheed_filename="2017-06-30_Ga.txt")
    calib_As = Calibration("As")
    ...
    # Define growth parameters
    rate_ga = 1.0 # 1.0 A/s deposition rate (2D film equivalent)
    rate_in = 0.2 # 0.2 A/s deposition rate (2D film equivalent)
    ftr_gaas = 80 # V/III ratio for GaAs growth
    ftr_inas = 110 # V/III ratio for InAs growth
    T_Ga = calib_Ga.calc_setpoint_gr(rate_ga) # Get Ga cell temperature
    T_In = calib_In.calc_setpoint_gr(rate_in) # Get In cell temperature 
    p_as_gaas = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas)  # Desired As pressure for GaAs growth
    p_as_inas = calib_In.calc_p_arsenic(rate_in, ftr_inas)  # Desired As pressure for InAs growth
    as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
    as_valve_inas = calib_As.calc_setpoint(p_as_inas)

Once we have the cell temperatures and As valve opening value, we can set it whenever we want:

    mbe.set_param("AsCracker.Valve.OP", as_valve_gaas)
    mbe.shutter("As", True)
    ts_print("Ramping up Ga and In sources")
    mbe.set_param("Ga.PV.Rate", 40)
    mbe.set_param("Ga.OP.Rate", 0)
    mbe.set_param("Ga.PV.TSP", T_Ga)
    mbe.set_param("In.PV.Rate", 15)
    mbe.set_param("In.OP.Rate", 0)
    mbe.set_param("In.PV.TSP", T_In)

## Virtual MBE
A second big motivation behind moving to a Python environment was the ability to create a Virtual MBE for testing recipes. Python itself, being an interpreted language, has the disadvantage in this sort of application that if an error is made in the script, it will only get detected at runtime. Therefore, if a syntax error is made at line 80/100, the script will crash only once it comes time to execute that line and will thus likely result in a failed growth. The Virtual MBE feature was developed both for this reason, and the more general reason which is that being able to perform a "dry run" and get feedback if a prototype recipe is working as expected is very valuable. Being able to run a recipe virtually means that samples can be saved from potential failed growths caused by untested recipes.

I therefore incorporated a virtual MBE server host which can be run in parallel with the real MBE server host. When the user wants to test their recipe, they only need to set a flag and all of the recipe commands get sent to the virtual MBE host server instead of the real one. After the growth is finished, the virtual MBE server outputs a log file and a PNG image summarizing the growth for the grower to consult. Though it's not a vectorized format, PNG was chosen as the output format for easier viewing and thumbnail generation (compared to PDF) in the Windows file explorer.

An example of the output from a virtual MBE growth is shown here:
![Virtual MBE Growth](https://github.com/Martin09/MBEToolbox/raw/master/Virtual_MBE_Output/ExampleVirtualMBEOutput.png)
