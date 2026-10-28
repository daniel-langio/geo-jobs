package app.bpartners.geojobs.service.cityjson.texture;

import app.bpartners.geojobs.repository.model.cityjson.CityJSONRequest;
import app.bpartners.geojobs.repository.model.cityjson.CityJSONTexture;
import app.bpartners.geojobs.service.GeometrySquareMeterArea;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Showcase harness: texture each real dataset and copy the result, without any assertion. */
class ShowcaseTest {
  private static final GeometrySquareMeterArea projector = new GeometrySquareMeterArea();
  private static final ObjectMapper om = new ObjectMapper();
  private static final CityJsonTextureComputer subject =
      new CityJsonTextureComputer(
          new CityJsonIOService(om, projector), new CityJsonTextureDomainService(om, projector));

  @Test
  void showcase() throws Exception {
    var in = Path.of(System.getProperty("showcase.in", ".showcase/inputs"));
    var out = Path.of(System.getProperty("showcase.out", "build/showcase"));
    Files.createDirectories(out);
    run(in, out, "test2", "jpg", 265541, 180308);
    run(in, out, "roof7", "jpg", 261779, 185145);
    run(in, out, "roof7_roofer", "jpg", 261779, 185145, "roof7");
    run(in, out, "switzerland", "jpg", 271136, 186147);
  }

  private static void run(Path in, Path out, String name, String ext, int x, int y)
      throws Exception {
    run(in, out, name, ext, x, y, name);
  }

  private static void run(Path in, Path out, String name, String ext, int x, int y, String img)
      throws Exception {
    try {
      var texture =
          CityJSONTexture.builder()
              .zoom(19)
              .tileX(x)
              .tileY(y)
              .imageWidth(3072)
              .imageHeight(3072)
              .imageUri(in.resolve(img + "." + ext).toAbsolutePath().toString())
              .tileImageSizePx(1024)
              .build();
      var request = CityJSONRequest.builder().textures(List.of(texture)).build();
      File actual = subject.applyTexture(request, in.resolve(name + ".json").toFile());
      Files.copy(actual.toPath(), out.resolve(name + ".json"), StandardCopyOption.REPLACE_EXISTING);
    } catch (Throwable t) {
      Files.writeString(out.resolve(name + ".error.txt"), String.valueOf(t));
    }
  }
}
