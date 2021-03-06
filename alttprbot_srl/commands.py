import argparse
import shlex
import sys

import ircmessage

from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import (config, spoiler_races, srl_races,
                                tournament_results)
from alttprbot.exceptions import SahasrahBotException
from alttprbot.smz3gen import spoilers as smz3_spoilers
from alttprbot.tournament import league
from alttprbot.util.srl import get_race, srl_race_id

ACCESSIBLE_RACE_WARNING = ircmessage.style('WARNING: ', bold=True, fg='red') + ircmessage.style('This race is using an accessible ruleset that prohibits most sequence breaking glitches.  Please visit https://link.alttpr.com/accessible for more details!', fg='red')

async def handler(target, source, message, client):
    if not message[0] == '$':
        return

    try:
        args = await parse_args(message)
    except argparse.ArgumentError as err:
        if not target == '#speedrunslive':
            await client.message(target, err.message)
        return

    festivemode = await config.get(0, 'FestiveMode') == "true"
    post_start_message = None

    if args.command == '$preset' and target.startswith('#srl-'):
        srl_id = srl_race_id(target)
        srl = await get_race(srl_id)
        await client.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        race = await srl_races.get_srl_race_by_id(srl_id)

        if race:
            raise SahasrahBotException("There is already a game generated for this room.  To cancel it, use the $cancel command.")

        if srl['game']['abbrev'] == 'alttphacks':
            seed, preset_dict = await preset.get_preset(args.preset, hints=args.hints, spoilers="off")
            goal = f"vt8 randomizer - {preset_dict['goal_name']}"
            if args.accessible and seed.data['spoiler']['meta']['logic'] == 'NoGlitches':
                goal = f"{goal} - accessible ruleset"
                await client.message(target, ACCESSIBLE_RACE_WARNING)
                post_start_message = ACCESSIBLE_RACE_WARNING
            code = await seed.code()
            if args.silent:
                await client.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
            else:
                await client.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
        elif srl['game']['abbrev'] == 'alttpsm':
            seed, preset_dict = await preset.get_preset(args.preset, randomizer='smz3')
            goal = preset_dict['goal_name']
            if args.silent:
                await client.message(target, f"{goal} - {args.preset} - {seed.url}")
            else:
                await client.message(target, f".setgoal {goal} - {args.preset} - {seed.url}")
        else:
            raise SahasrahBotException("This game is not yet supported.")

        await srl_races.insert_srl_race(srl_id, goal, post_start_message)

    if args.command in ['$mystery', '$festivemystery'] and target.startswith('#srl-'):
        mode = "mystery"
        festive = True if args.command in ['$festivemystery'] and festivemode else False

        srl_id = srl_race_id(target)
        srl = await get_race(srl_id)
        await client.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        race = await srl_races.get_srl_race_by_id(srl_id)

        if race:
            raise SahasrahBotException("There is already a game generated for this room.  To cancel it, use the $cancel command.")

        if srl['game']['abbrev'] == 'alttphacks':
            seed = await mystery.generate_random_game(
                weightset=args.weightset,
                tournament=True,
                spoilers="off" if mode == "random" else "mystery",
                festive=festive
            )

            code = await seed.code()

            if festive:
                goal = f"vt8 randomizer - festive {mode} {args.weightset} - DO NOT RECORD"
            else:
                goal = f"vt8 randomizer - {mode} {args.weightset}"

            if args.accessible and seed.data['spoiler']['meta']['logic'] == 'NoGlitches':
                goal = f"{goal} - accessible ruleset"
                await client.message(target, ACCESSIBLE_RACE_WARNING)
                post_start_message = ACCESSIBLE_RACE_WARNING

            if args.silent:
                await client.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
            else:
                await client.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
        else:
            raise SahasrahBotException("This game is not yet supported.")

        await srl_races.insert_srl_race(srl_id, goal, post_start_message)

    if args.command == '$custom' and target.startswith('#srl-'):
        await client.message(target, "Not yet implemented.  Sorry!")

    if args.command == '$spoiler' and target.startswith('#srl-'):
        srl_id = srl_race_id(target)
        srl = await get_race(srl_id)
        await client.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        race = await srl_races.get_srl_race_by_id(srl_id)

        if race:
            raise SahasrahBotException("There is already a game generated for this room.  To cancel it, use the $cancel command.")

        if srl['game']['abbrev'] == 'alttphacks':
            seed, preset_dict, spoiler_log_url = await spoilers.generate_spoiler_game(args.preset)

            goal_name = preset_dict['goal_name']

            if not seed:
                return

            goal = f"vt8 randomizer - spoiler {goal_name}"

            if args.accessible and seed.data['spoiler']['meta']['logic'] == 'NoGlitches':
                goal = f"{goal} - accessible ruleset"
                await client.message(target, ACCESSIBLE_RACE_WARNING)
                post_start_message = ACCESSIBLE_RACE_WARNING

            studytime = 900 if not args.studytime else args.studytime
            code = await seed.code()
            if args.silent:
                await client.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
            else:
                await client.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
            await client.message(target, f"The spoiler log for this race will be sent after the race begins in SRL.  A {studytime}s countdown timer at that time will begin.")
        elif srl['game']['abbrev'] == 'alttpsm':
            seed, spoiler_log_url = await smz3_spoilers.generate_spoiler_game(args.preset)

            if seed is None:
                raise SahasrahBotException("That preset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live")

            goal = f"spoiler beat the games"
            studytime = 1500 if not args.studytime else args.studytime
            if args.silent:
                await client.message(target, f"{goal} - {seed.url}")
            else:
                await client.message(target, f".setgoal {goal} - {seed.url}")
            await client.message(target, f"The spoiler log for this race will be sent after the race begins in SRL.  A {studytime}s countdown timer at that time will begin.")
        else:
            await client.message(target, "This game is not yet supported.")
            return

        await srl_races.insert_srl_race(srl_id, goal, post_start_message)
        await spoiler_races.insert_spoiler_race(srl_id, spoiler_log_url, studytime)

    if args.command == '$leaguerace' and target.startswith('#srl-'):
        await league.process_league_race(target, args, client)

    if args.command == '$cancel' and target.startswith('#srl-'):
        srl_id = srl_race_id(target)
        await srl_races.delete_srl_race(srl_id)
        await spoiler_races.delete_spoiler_race(srl_id)
        await tournament_results.delete_active_touranment_race(srl_id)
        await client.message(target, "Current race cancelled.")
        await client.message(target, f".setgoal new race")

    if args.command == '$rules' and target.startswith('#srl-'):
        await client.message(target, "For the ALTTPR rules for this race, visit https://link.alttpr.com/racerules")

    if args.command == '$accessible' and target.startswith('#srl-'):
        await client.message(target, "For the ALTTPR accessible racing rules, visit https://link.alttpr.com/accessible")

    if args.command == '$help':
        await client.message(target, "For documentation on using this bot, visit https://sahasrahbot.synack.live")

    if args.command == '$joinroom':
        await client.join(args.channel)

    if args.command == '$leave' and target.startswith('#srl-'):
        await client.part(target)

    if args.command == '$vt' and target.startswith('#srl-'):
        await client.message(target, "You summon VT, he looks around confused and curses your next game with bad RNG.")


async def parse_args(message):
    split_msg = ['sb'] + shlex.split(message)

    parser = SrlArgumentParser()
    parser.add_argument('base', type=str)

    subparsers = parser.add_subparsers(dest="command")

    parser_preset = subparsers.add_parser('$preset')
    parser_preset.add_argument('preset')
    parser_preset.add_argument('--hints', action='store_true')
    parser_preset.add_argument('--silent', action='store_true')
    parser_preset.add_argument('--accessible', action='store_true')

    subparsers.add_parser('$custom')

    parser_spoiler = subparsers.add_parser('$spoiler')
    parser_spoiler.add_argument('preset')
    parser_spoiler.add_argument('--studytime', type=int)
    parser_spoiler.add_argument('--silent', action='store_true')
    parser_spoiler.add_argument('--accessible', action='store_true')

    parser_mystery = subparsers.add_parser('$mystery')
    parser_mystery.add_argument('weightset', nargs='?', default="weighted")
    parser_mystery.add_argument('--silent', action='store_true')
    parser_mystery.add_argument('--accessible', action='store_true')

    if await config.get(0, 'FestiveMode') == "true":
        parser_festivemystery = subparsers.add_parser('$festivemystery')
        parser_festivemystery.add_argument(
            'weightset', nargs='?', default="weighted")
        parser_festivemystery.add_argument('--silent', action='store_true')
        parser_preset.add_argument('--accessible', action='store_true')

    parser_leaguerace = subparsers.add_parser('$leaguerace')
    parser_leaguerace.add_argument('episodeid')
    parser_leaguerace.add_argument('--week', default=None)

    parser_join = subparsers.add_parser('$joinroom')
    parser_join.add_argument('channel')

    subparsers.add_parser('$leave')

    subparsers.add_parser('$cancel')

    subparsers.add_parser('$vt')

    subparsers.add_parser('$rules')

    parser_echo = subparsers.add_parser('$echo')
    parser_echo.add_argument('message')

    subparsers.add_parser('$help')

    args = parser.parse_args(split_msg)

    return args


class SrlArgumentParser(argparse.ArgumentParser):
    def _get_action_from_name(self, name):
        """Given a name, get the Action instance registered with this parser.
        If only it were made available in the ArgumentError object. It is
        passed as it's first arg...
        """
        container = self._actions
        if name is None:
            return None
        for action in container:
            if '/'.join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        exc = sys.exc_info()[1]
        if exc:
            exc.argument = self._get_action_from_name(exc.argument_name)
            raise exc
        # super(SrlArgumentParser, self).error(message)
