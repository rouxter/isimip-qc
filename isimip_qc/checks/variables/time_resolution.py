import calendar

import netCDF4
from isimip_qc.config import settings


def check_time_resolution(file):
    time = file.dataset.variables.get('time')
    time_definition = settings.DEFINITIONS['dimensions'].get('time')
    time_resolution = file.specifiers.get('time_step')

    try:
        time_units = time.units
    except AttributeError:
        file.warn('Can\'t check for number of time steps because of missing time.units attribute')
        return

    if time_resolution == 'daily':
        try:
            time_calendar = time.calendar
        except AttributeError:
            file.warn('Can\'t check for number of time steps because of missing time.calendar attribute')
            return
    if time_resolution == 'monthly':
        # for monthly resolution cftime.num2date only allows for '360_day' calendar
        time_calendar = '360_day'

    if all([time, time_definition, time_resolution, time_units, time_calendar]):
        # first and last year from file name specifiers must match those from internal time axis
        # number of time steps must match those expected from the time axis
        time_steps = len(time[:])

        if time_resolution in ['daily', 'monthly']:
            firstdate_nc = netCDF4.num2date(time[0], time_units, time_calendar)
            lastdate_nc = netCDF4.num2date(time[time_steps-1], time_units, time_calendar)
            startyear_nc = firstdate_nc.year
            endyear_nc = lastdate_nc.year
        elif time_resolution == 'annual':
            ref_year = int(time.units.split()[2].split("-")[0])
            startyear_nc = ref_year + int(time[0])
            endyear_nc = ref_year + int(time[-1])

        startyear_file = int(file.specifiers.get('start_year'))
        endyear_file = int(file.specifiers.get('end_year'))
        nyears_file = endyear_file - startyear_file + 1

        if startyear_nc != startyear_file or endyear_nc != endyear_file:
            file.error('Start and/or end year of NetCDF time axis (%s-%s) doesn\'t match period defined in file name (%s-%s)', startyear_nc, endyear_nc, startyear_file, endyear_file)
        else:
            file.info('Time period covered by this file matches the internal time axis (%s-%s)', startyear_nc, endyear_nc)

        if time_resolution == 'daily':
            if time_calendar in ['proleptic_gregorian', 'standard']:
                time_days = 0
                for year in range(startyear_file, endyear_file+1):
                    if calendar.isleap(year):
                        time_days += 366
                    else:
                        time_days += 365
            elif time_calendar == '366_day':
                time_days = nyears_file * 366
            elif time_calendar == '365_day':
                time_days = nyears_file * 365
            elif time_calendar == '360_day':
                time_days = nyears_file * 360

            if time_days != time_steps:
                file.error('Number of internal time steps (%s) does not match the expected number from the file name specifiers (%s). (\'%s\' calendar found)', time_steps, time_days, time_calendar)
            else:
                file.info('Correct number of time steps (%s) given the defined calendar (%s)', time_steps, time_calendar)
        elif time_resolution == 'monthly':
            time_months = nyears_file * 12
            if time_months != time_steps:
                file.error('Number of internal time steps (%s) does not match the expected number from the file name specifiers (%s).', time_steps, time_months)
            else:
                file.info('Correct number of time steps (%s).', time_steps)
        elif time_resolution == 'annual':
            if nyears_file != time_steps:
                file.error('Number of internal time steps (%s) does not match the expected number from the file name specifiers (%s).', time_steps, nyears_file)
            else:
                file.info('Correct number of time steps (%s).', time_steps)