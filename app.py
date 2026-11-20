from flask import Flask, render_template, request
from datetime import datetime, timedelta

app = Flask(__name__)


# ==========================================
# HOME PAGE
# ==========================================

@app.route('/')
def home():

    return render_template('index.html')


# ==========================================
# SINGLE EV CHARGING SCHEDULER
# ==========================================

@app.route('/schedule', methods=['POST'])
def schedule():

    try:

        # Vehicle information

        vehicle = request.form.get('vehicle')
        battery = float(request.form.get('battery'))
        required = float(request.form.get('required'))

        capacity = float(request.form.get('capacity'))
        charging_power = float(request.form.get('charging_power'))

        departure = request.form.get('departure')

        # Solar information

        solar_power = float(request.form.get('solar_power'))

        solar_start = request.form.get('solar_start')
        solar_end = request.form.get('solar_end')

        # Electricity price

        electricity_price = float(
            request.form.get('electricity_price')
        )

        # Validation

        if not all([vehicle, departure, solar_start, solar_end]):
            raise ValueError("Please enter all required details.")

        if not (0 <= battery < required <= 100):
            raise ValueError("Check the battery percentages.")

        if capacity <= 0 or charging_power <= 0:
            raise ValueError("Capacity and charging power must be positive.")

        if solar_power < 0 or electricity_price < 0:
            raise ValueError("Solar power and electricity price cannot be negative.")

        # Energy calculation

        energy_needed = capacity * (required - battery) / 100

        charging_time = energy_needed / charging_power

        # Convert time

        start = datetime.strptime(solar_start, "%H:%M")
        end = datetime.strptime(solar_end, "%H:%M")
        departure_time = datetime.strptime(departure, "%H:%M")

        if end <= start:
            raise ValueError("Solar end time must be later than solar start time.")

        if departure_time <= start:
            raise ValueError("Departure must be later than solar start time.")

        # Solar availability

        solar_hours = (
            end - start
        ).total_seconds() / 3600

        solar_charging_hours = min(
            charging_time,
            solar_hours
        )

        # Energy supplied

        solar_used = (
            min(solar_power, charging_power)
            * solar_charging_hours
        )

        grid_energy = max(
            0,
            energy_needed - solar_used
        )

        solar_available = solar_power * solar_hours

        # Charging completion

        if charging_time <= solar_hours:

            finish_time = start + timedelta(
                hours=charging_time
            )

        else:

            finish_time = end + timedelta(
                hours=charging_time - solar_hours
            )

        charging_possible = (
            finish_time <= departure_time
        )

        # Solar percentage

        solar_percentage = (
            solar_used / energy_needed
        ) * 100

        # Cost calculation

        grid_only_cost = (
            energy_needed * electricity_price
        )

        solar_charging_cost = (
            grid_energy * electricity_price
        )

        money_saved = (
            grid_only_cost - solar_charging_cost
        )

        savings_percentage = (
            money_saved / grid_only_cost
        ) * 100 if grid_only_cost > 0 else 0

        # Charging schedule

        if not charging_possible:

            schedule_message = (
                "Charging cannot be completed before departure."
            )

        elif solar_used > 0:

            schedule_message = (
                f"Start charging at {start.strftime('%H:%M')}. "
                f"Estimated completion: {finish_time.strftime('%H:%M')}."
            )

        else:

            schedule_message = (
                "Grid-only charging is required."
            )

        # Display results

        return render_template(

            'index.html',

            vehicle=vehicle,
            battery=battery,
            required=required,
            departure=departure,

            energy=round(energy_needed, 2),
            charging_time=round(charging_time, 2),

            solar_available=round(solar_available, 2),
            solar_used=round(solar_used, 2),
            grid_energy=round(grid_energy, 2),

            solar_percentage=round(solar_percentage, 2),

            electricity_price=electricity_price,

            grid_only_cost=round(grid_only_cost, 2),
            solar_charging_cost=round(solar_charging_cost, 2),

            money_saved=round(money_saved, 2),
            savings_percentage=round(savings_percentage, 2),

            schedule_message=schedule_message,
            charging_possible=charging_possible

        )

    except (ValueError, TypeError) as error:

        return render_template(
            'index.html',
            error=str(error)
        )


# ==========================================
# MULTIPLE EV FLEET MANAGEMENT
# ==========================================

@app.route('/fleet', methods=['GET', 'POST'])
def fleet():

    # Open fleet page

    if request.method == 'GET':

        return render_template(
            'fleet.html',
            results=None
        )

    try:

        vehicles = []

        # Solar information

        solar_power = float(
            request.form.get('solar_power')
        )

        if solar_power < 0:
            raise ValueError(
                "Solar power cannot be negative."
            )

        # Collect three vehicle details

        for i in range(1, 4):

            vehicle = request.form.get(
                f'vehicle{i}'
            )

            battery = float(
                request.form.get(f'battery{i}')
            )

            required = float(
                request.form.get(f'required{i}')
            )

            capacity = float(
                request.form.get(f'capacity{i}')
            )

            power = float(
                request.form.get(f'power{i}')
            )

            departure = request.form.get(
                f'departure{i}'
            )

            # Validate details

            if not vehicle or not departure:

                raise ValueError(
                    f"Please enter all details for Vehicle {i}."
                )

            if not (0 <= battery < required <= 100):

                raise ValueError(
                    f"Check battery percentages for Vehicle {i}."
                )

            if capacity <= 0 or power <= 0:

                raise ValueError(
                    f"Capacity and charging power must be positive for Vehicle {i}."
                )

            # Calculate energy

            energy = (
                capacity * (required - battery) / 100
            )

            # Calculate charging duration

            duration = energy / power

            # Convert departure time

            departure_minutes = (
                int(departure[:2]) * 60
                + int(departure[3:5])
            )

            # Store vehicle information

            vehicles.append({

                'vehicle': vehicle,

                'battery': battery,

                'required': required,

                'capacity': capacity,

                'power': power,

                'energy': energy,

                'duration': duration,

                'departure_minutes': departure_minutes,

                'departure': departure

            })

        # ==================================
        # PRIORITY MANAGEMENT
        # ==================================

        # Sort vehicles by earliest departure

        vehicles.sort(
            key=lambda x: x['departure_minutes']
        )

        # ==================================
        # CHARGING SCHEDULE
        # ==================================

        # Charging starts at 09:00

        current_time = 9 * 60

        results = []

        total_energy = 0

        # Process each vehicle

        for index, vehicle in enumerate(vehicles):

            start_time = current_time

            duration_minutes = (
                vehicle['duration'] * 60
            )

            finish_time = (
                start_time + duration_minutes
            )

            # Convert minutes into time format

            def format_time(minutes):

                minutes = round(minutes) % 1440

                hours = minutes // 60

                mins = minutes % 60

                return f"{hours:02d}:{mins:02d}"

            # Check departure deadline

            if finish_time <= vehicle['departure_minutes']:

                status = "Ready before departure"

            else:

                status = "Charging finishes after departure"

            # Prepare results

            results.append({

                'vehicle': vehicle['vehicle'],

                'battery': vehicle['battery'],

                'required': vehicle['required'],

                'energy': round(vehicle['energy'], 2),

                'duration': round(vehicle['duration'], 2),

                'departure': vehicle['departure'],

                'priority': f"Priority {index + 1}",

                'start': format_time(start_time),

                'finish': format_time(finish_time),

                'status': status

            })

            # Calculate total energy

            total_energy += vehicle['energy']

            # Move to next charging slot

            current_time = finish_time

        # ==================================
        # DISPLAY FLEET RESULTS
        # ==================================

        return render_template(

            'fleet.html',

            results=results,

            total_energy=round(total_energy, 2)

        )

    except (ValueError, TypeError) as error:

        return render_template(

            'fleet.html',

            results=None,

            error=str(error)

        )


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == '__main__':

    app.run(debug=True)