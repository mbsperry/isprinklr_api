"""
CLI configuration tool for the iSprinklr API.

This script provides commands to configure essential settings for the iSprinklr system,
including API settings and sprinkler zone configurations. It can be run from the command
line to set up or update API configuration (including domain, ESP controller IP, dummy mode,
schedule settings, log level, and CORS security settings) and sprinkler zone definitions.
"""

import typer
import json
import os
from typing import List

try:
    from isprinklr.paths import config_path, data_path
    from isprinklr.schemas import SprinklerConfig
    from isprinklr.sprinkler_service import write_sprinklers, validate_sprinklers
except ImportError as e:
    typer.echo(f"Error: Could not import isprinklr package components: {e}", err=True)
    typer.echo("Please ensure you are running this script from the project root directory.", err=True)
    raise typer.Exit(code=1)


app = typer.Typer(invoke_without_command=True)

@app.command()
def config_api():
    """
    Configure the API settings in config/api.conf.
    
    Reads existing settings if present, then prompts the user for each configuration
    value. Default values are provided based on existing settings or sensible defaults.
    Settings include domain, ESP controller IP, dummy mode status, schedule status, 
    log level, and CORS security settings.
    
    Raises:
        typer.Exit: If there is an error writing the configuration file.
    """
    api_conf_path = os.path.join(config_path, "api.conf")
    current_config = {}

    typer.echo("\n--- API Configuration ---")

    if os.path.exists(api_conf_path):
        try:
            with open(api_conf_path, "r") as f:
                current_config = json.load(f)
            typer.echo(f"Found existing config at '{api_conf_path}'. Current values:")
            typer.echo(json.dumps(current_config, indent=2))
        except json.JSONDecodeError:
            typer.echo(f"Warning: Existing '{api_conf_path}' is not valid JSON. Starting with empty config.", err=True)
            current_config = {}
        except Exception as e:
            typer.echo(f"Warning: Could not read '{api_conf_path}': {e}. Starting with empty config.", err=True)
            current_config = {}
    else:
        typer.echo(f"'{api_conf_path}' not found. Starting with empty config.")

    typer.echo("\nEnter values for api.conf (press Enter to keep current or use default):")

    default_domain = current_config.get("domain", "localhost")
    domain = typer.prompt(f"Domain (default: {default_domain})", default=default_domain)
    current_config["domain"] = domain if domain else default_domain

    default_esp_ip = current_config.get("ESP_controller_IP", "")
    esp_ip = typer.prompt(f"ESP Controller IP (default: {default_esp_ip})", default=default_esp_ip)
    current_config["ESP_controller_IP"] = esp_ip if esp_ip else default_esp_ip

    inferred_default_dummy = not current_config.get("ESP_controller_IP") if current_config.get("ESP_controller_IP") is not None else True
    default_dummy_mode = current_config.get("dummy_mode", inferred_default_dummy)
    dummy_mode_str = typer.prompt(f"Dummy Mode (True/False, default: {default_dummy_mode})", default=str(default_dummy_mode))
    dummy_mode = dummy_mode_str.lower() in ["true", "yes", "on", "1"]
    current_config["dummy_mode"] = dummy_mode

    default_schedule_on_off = current_config.get("schedule_on_off", False)
    schedule_on_off_str = typer.prompt(f"Schedule ON/OFF (True/False, default: {default_schedule_on_off})", default=str(default_schedule_on_off))
    schedule_on_off = schedule_on_off_str.lower() in ["true", "yes", "on", "1"]
    current_config["schedule_on_off"] = schedule_on_off

    default_log_level = current_config.get("log_level", "INFO")
    log_level = typer.prompt(f"Log Level (DEBUG, INFO, WARNING, ERROR, CRITICAL, default: {default_log_level})", default=default_log_level)
    current_config["log_level"] = log_level.upper()

    default_use_strict_cors = current_config.get("USE_STRICT_CORS", False)
    use_strict_cors_str = typer.prompt(f"Use Strict CORS (True/False, default: {default_use_strict_cors})", default=str(default_use_strict_cors))
    use_strict_cors = use_strict_cors_str.lower() in ["true", "yes", "on", "1"]
    current_config["USE_STRICT_CORS"] = use_strict_cors

    if not os.path.exists(config_path):
        os.makedirs(config_path)

    try:
        with open(api_conf_path, "w") as f:
            json.dump(current_config, f, indent=2)
        typer.echo(f"\nSuccessfully wrote config to '{api_conf_path}'.")
        typer.echo("Please review the file.")
    except Exception as e:
        typer.echo(f"\nError writing config to '{api_conf_path}': {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def config_sprinklers():
    """
    Configure the sprinkler zones in data/sprinklers.json.
    
    Reads existing sprinkler configuration if present. Prompts the user to configure
    each zone from 1 to 12, allowing them to set names for each zone. User can press
    Enter to use default names, type 'done' to finish configuration, or 'cancel' to
    abort without saving.
    
    Raises:
        typer.Exit: If validation fails or there is an error writing the sprinkler config.
    """
    sprinklers_json_path = os.path.join(data_path, "sprinklers.json")
    current_sprinklers: List[SprinklerConfig] = []

    typer.echo("\n--- Sprinkler Configuration ---")

    if os.path.exists(sprinklers_json_path):
        try:
            with open(sprinklers_json_path, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    try:
                        if data: 
                             validate_sprinklers(data)
                        current_sprinklers = data
                        typer.echo(f"Found existing sprinkler config at '{sprinklers_json_path}'. Current zones:")
                        for s in current_sprinklers:
                            typer.echo(f"  Zone {s.get('zone', 'N/A')}: {s.get('name', 'N/A')}")
                    except ValueError as e:
                         typer.echo(f"Warning: Existing '{sprinklers_json_path}' contains invalid sprinkler data: {e}. Starting with empty list.", err=True)
                         current_sprinklers = []
                else:
                    typer.echo(f"Warning: Existing '{sprinklers_json_path}' is not a list. Found type: {type(data).__name__}. Starting with empty list.", err=True)
                    current_sprinklers = []
        except json.JSONDecodeError:
            typer.echo(f"Warning: Existing '{sprinklers_json_path}' is not valid JSON. Starting with empty list.", err=True)
            current_sprinklers = []
        except Exception as e:
            typer.echo(f"Warning: Could not read '{sprinklers_json_path}': {e}. Starting with empty list.", err=True)
            current_sprinklers = []
    else:
        typer.echo(f"'{sprinklers_json_path}' not found. Starting with empty list.")

    current_sprinklers_dict = {s['zone']: s for s in current_sprinklers if 'zone' in s}

    typer.echo("\nEnter sprinkler zone configurations, starting with Zone 1.")
    typer.echo("Press Enter to use the existing name or default 'Zone [number]'.")
    typer.echo("Enter 'done' to finish and save.")
    typer.echo("Enter 'cancel' to abort without saving.")

    new_sprinklers: List[SprinklerConfig] = []
    zone_number = 1
    max_zones = 12

    while zone_number <= max_zones:
        existing_sprinkler = current_sprinklers_dict.get(zone_number)
        default_name = existing_sprinkler['name'] if existing_sprinkler and 'name' in existing_sprinkler else f"Zone {zone_number}"

        name_input = typer.prompt(
            f"Enter Name for Zone {zone_number} (default: '{default_name}', 'done' to finish, 'cancel' to abort)",
            default=default_name
        )

        stripped_name_input = name_input.strip()

        if stripped_name_input.lower() == 'cancel':
            typer.echo("Sprinkler configuration cancelled. No changes saved.", err=True)
            return

        if stripped_name_input.lower() == 'done':
            typer.echo("Finishing sprinkler configuration.")
            break

        if not stripped_name_input:
            typer.echo("Name cannot be empty or just whitespace. Please try again.", err=True)
            continue

        name_to_use = stripped_name_input
        
        if name_to_use == default_name and name_input == default_name:
             typer.echo(f"Using name: '{name_to_use}' for Zone {zone_number}")

        new_sprinklers.append({"zone": zone_number, "name": name_to_use})
        zone_number += 1

    if not new_sprinklers:
         typer.echo("No sprinkler zones configured. Exiting without saving.", err=True)
         return

    try:
        validate_sprinklers(new_sprinklers)
    except ValueError as e:
        typer.echo(f"Validation failed for configured sprinklers: {e}", err=True)
        typer.echo("Aborting write.", err=True)
        raise typer.Exit(code=1)

    if not os.path.exists(data_path):
        os.makedirs(data_path)

    try:
        write_sprinklers(data_path, new_sprinklers)
        typer.echo(f"\nSuccessfully wrote sprinkler configurations to '{sprinklers_json_path}'.")

    except Exception as e:
        typer.echo(f"\nError writing sprinkler configurations to '{sprinklers_json_path}': {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def full_setup():
    """
    Run both API and sprinkler configuration commands sequentially.
    
    This is a convenience command that runs both config_api and config_sprinklers
    in sequence, allowing for a complete setup of the iSprinklr system in one go.
    """
    config_api()
    config_sprinklers()
    typer.echo("\nSetup process finished.")


@app.callback()
def main_callback(ctx: typer.Context):
    """
    Default behavior when no command is provided:
    Runs config_api, then asks if the user wants to proceed with sprinkler configuration.
    """
    if ctx.invoked_subcommand is None:
        config_api()
        if typer.confirm("Would you like to proceed with sprinkler zone configuration?"):
            config_sprinklers()

if __name__ == "__main__":
    app()
