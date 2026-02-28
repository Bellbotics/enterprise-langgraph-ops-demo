package demo;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/demo")
public class DemoController {

  private final AtomicInteger simulatedPoolAvailable = new AtomicInteger(20);

  @GetMapping("/health")
  public Map<String, Object> health() {
    return Map.of("ok", true, "simulatedPoolAvailable", simulatedPoolAvailable.get());
  }

  @PostMapping("/simulate/hikari")
  public ResponseEntity<?> simulateHikari(@RequestParam(defaultValue = "25") int concurrent) {
    // Simulate pool starvation: if concurrent > available, respond with 503.
    int available = simulatedPoolAvailable.get();
    if (concurrent > available) {
      return ResponseEntity.status(503).body(Map.of(
          "error", "HikariPool - Connection is not available",
          "available", available,
          "requested", concurrent
      ));
    }
    return ResponseEntity.ok(Map.of("ok", true, "available", available, "requested", concurrent));
  }

  @PostMapping("/simulate/pdf")
  public ResponseEntity<?> simulatePdf(@RequestParam(defaultValue = "500") int mb) {
    // Simulate memory pressure signal (does not actually allocate huge memory for safety).
    // Returns a payload indicating a heavy job.
    return ResponseEntity.status(202).body(Map.of(
        "accepted", true,
        "jobType", "pdf_watermark",
        "estimatedMemoryMb", mb,
        "note", "Demo endpoint: indicates heavy job that should be routed to a worker lane."
    ));
  }
}
