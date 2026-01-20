library(ggplot2)
library(dplyr)
library(tidyr)
library(patchwork)

people <- c("Wenbin Wu", "Philipp Chapkovski", "Mariol Jonuzaj")
colors <- c("#2ecc71", "#e67e22", "#3498db")

totals <- data.frame(
  person = factor(people, levels = people),
  commits = c(495, 137, 79),
  lines_added = c(86315, 7775, 2365)
)

months <- c("Aug23", "Sep23", "Nov23", "Dec23", "Jan24", "Feb24", "Mar24", "Apr24", 
            "May24", "Jun24", "Jul24", "Aug24", "Sep24", "Oct24", "Nov24", "Dec24",
            "Jan25", "Feb25", "Mar25", "Apr25", "May25", "Jun25", "Aug25", "Sep25", 
            "Oct25", "Nov25", "Dec25", "Jan26")

monthly <- data.frame(
  month = factor(rep(months, 3), levels = months),
  person = factor(rep(people, each = 28), levels = people),
  commits = c(
    0, 0, 0, 0, 0, 3, 10, 9, 17, 10, 68, 28, 48, 65, 58, 2, 12, 11, 20, 4, 8, 45, 11, 8, 14, 13, 22, 9,
    13, 36, 14, 2, 3, 20, 36, 12, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 16, 11, 9, 10, 0, 1, 11, 3, 4, 0, 3, 6, 4, 0, 0
  )
)

p1 <- ggplot(totals, aes(x = person, y = lines_added/1000, fill = person)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = paste0(round(lines_added/sum(lines_added)*100, 1), "%")), vjust = -0.5, size = 4) +
  scale_fill_manual(values = colors) +
  labs(title = "Total Lines of Code Added", y = "Lines (thousands)", x = "") +
  theme_minimal() +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1))

p2 <- ggplot(totals, aes(x = person, y = commits, fill = person)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = paste0(commits, "\n(", round(commits/sum(commits)*100, 1), "%)")), vjust = -0.3, size = 3.5) +
  scale_fill_manual(values = colors) +
  labs(title = "Total Git Commits", y = "Commits", x = "") +
  theme_minimal() +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1))

p3 <- ggplot(monthly, aes(x = month, y = commits, color = person, group = person)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = colors) +
  labs(title = "Monthly Git Commits (Aug 2023 - Jan 2026)", y = "Commits", x = "", color = "") +
  theme_minimal() +
  theme(legend.position = "bottom", axis.text.x = element_text(angle = 45, hjust = 1, size = 7)) +
  annotate("rect", xmin = 0.5, xmax = 9.5, ymin = -Inf, ymax = Inf, alpha = 0.1, fill = "#e67e22") +
  annotate("text", x = 5, y = 60, label = "Philipp's\nperiod", size = 3, color = "#e67e22")

p4 <- ggplot(totals, aes(x = "", y = lines_added, fill = person)) +
  geom_bar(stat = "identity", width = 1) +
  coord_polar("y") +
  scale_fill_manual(values = colors) +
  labs(title = "Code Contribution Share", fill = "") +
  theme_void() +
  theme(legend.position = "right") +
  geom_text(aes(label = paste0(round(lines_added/sum(lines_added)*100, 1), "%")),
            position = position_stack(vjust = 0.5), size = 4)

combined <- (p1 + p2) / (p3 + p4) +
  plot_annotation(title = "CODE CONTRIBUTION ANALYSIS",
                  subtitle = "trading_platform git repository | Aug 2023 - Jan 2026",
                  theme = theme(plot.title = element_text(face = "bold", size = 14)))

ggsave("code_contribution.png", combined, width = 14, height = 10, dpi = 150)
cat("Saved code_contribution.png\n")
