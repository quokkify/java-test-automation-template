package example.config;

import dev.quokkify.config.ConfigRegistry;

public final class StarterConfig {

  private static final StarterConfiguration CONFIG = ConfigRegistry.get(StarterConfiguration.class);

  public static final String MESSAGE = CONFIG.message();

  private StarterConfig() {
  }
}
