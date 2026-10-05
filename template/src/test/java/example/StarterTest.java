package example;

import example.config.StarterConfig;
import org.testng.annotations.Test;

import static org.testng.Assert.assertFalse;

public class StarterTest {

  @Test
  public void readsConfiguration() {
    assertFalse(StarterConfig.MESSAGE.isBlank());
  }
}
