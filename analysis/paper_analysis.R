library(ggplot2)
library(dplyr)
library(tidyr)
library(patchwork)

people <- c("Wenbin Wu", "Mariol Jonuzaj", "Alessio Sancetta")
colors <- c("#2ecc71", "#3498db", "#9b59b6")

totals <- data.frame(
  person = factor(people, levels = people),
  commits = c(15, 5, 17),
  lines_added = c(2976, 696, 56)
)

months <- c("Oct25", "Nov25", "Dec25", "Jan26")
monthly <- data.frame(
  month = factor(rep(months, 3), levels = months),
  person = factor(rep(people, each = 4), levels = people),
  commits = c(5, 3, 5, 2,
              1, 1, 1, 2,
              0, 0, 0, 17)
)

p1 <- ggplot(totals, aes(x = person, y = lines_added, fill = person)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = paste0(round(lines_added/sum(lines_added)*100, 1), "%")), vjust = -0.5, size = 4) +
  scale_fill_manual(values = colors) +
  labs(title = "Lines Added to Paper (.tex files)", y = "Lines", x = "") +
  theme_minimal() +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1))

p2 <- ggplot(totals, aes(x = person, y = commits, fill = person)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = commits), vjust = -0.5, size = 4) +
  scale_fill_manual(values = colors) +
  labs(title = "Git Commits to Paper Repo", y = "Commits", x = "") +
  theme_minimal() +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1))

p3 <- ggplot(monthly, aes(x = month, y = commits, fill = person)) +
  geom_bar(stat = "identity", position = "dodge") +
  scale_fill_manual(values = colors) +
  labs(title = "Monthly Commits to Paper (Oct 2025 - Jan 2026)", y = "Commits", x = "", fill = "") +
  theme_minimal() +
  theme(legend.position = "bottom")

p4 <- ggplot(totals, aes(x = "", y = lines_added, fill = person)) +
  geom_bar(stat = "identity", width = 1) +
  coord_polar("y") +
  scale_fill_manual(values = colors) +
  labs(title = "Paper Content Share\n(Lines Added)", fill = "") +
  theme_void() +
  theme(legend.position = "right") +
  geom_text(aes(label = paste0(round(lines_added/sum(lines_added)*100, 1), "%")),
            position = position_stack(vjust = 0.5), size = 4)

combined <- (p1 + p2) / (p3 + p4) +
  plot_annotation(title = "PAPER CONTRIBUTION ANALYSIS",
                  subtitle = "platform-paper git repository (Overleaf) | Oct 2025 - Jan 2026",
                  theme = theme(plot.title = element_text(face = "bold", size = 14)),
                  caption = "Note: Alessio's 17 commits are comments/reviews (only 56 lines added)")

ggsave("paper_contribution.png", combined, width = 12, height = 10, dpi = 150)
cat("Saved paper_contribution.png\n")
