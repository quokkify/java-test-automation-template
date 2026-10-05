package example.config;

import org.aeonbits.owner.Config;

@Config.LoadPolicy(Config.LoadType.MERGE)
@Config.Sources({"system:properties", "system:env", "classpath:starter.properties"})
interface StarterConfiguration extends Config {

  @Key("TEST_MESSAGE")
  String message();
}
