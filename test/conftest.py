from hypothesis import Verbosity, settings

settings.register_profile('ci', max_examples=1000, deadline=1000)
settings.register_profile("dev", max_examples=100)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
