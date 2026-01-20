library(ggplot2)
library(dplyr)
library(tidyr)
library(patchwork)

people <- c("Wenbin Wu", "Mariol Jonuzaj", "Alessio Sancetta", "Francesco Feri", "Michael Naef")
colors <- c("#2ecc71", "#3498db", "#9b59b6", "#e74c3c", "#f39c12")

totals <- data.frame(
  person = factor(people, levels = people),
  content_k = c(13026.9, 4784.9, 2520.9, 650.6, 212.4),
  emails_sent = c(669, 276, 162, 36, 16),
  threads_started = c(158, 79, 56, 14, 10)
)

months <- c("Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan")
monthly <- data.frame(
  month = factor(rep(months, 5), levels = months),
  person = factor(rep(people, each = 12), levels = people),
  chars_k = c(29.2, 108.9, 37.6, 15.7, 133.1, 1.6, 23.5, 103.9, 96.8, 170.3, 74.7, 81.9,
              66.3, 133.3, 41.7, 18.6, 44.6, 4.6, 19.1, 92.1, 78.4, 85.8, 119.2, 60.5,
              2.9, 11.1, 1.6, 3.2, 60.4, 2.8, 13.6, 18.7, 28.7, 26.8, 30.5, 46.0,
              8.0, 1.5, 0.7, 9.5, 3.2, 1.1, 16.7, 42.9, 23.5, 17.3, 49.8, 18.4,
              4.5, 0.0, 0.0, 0.0, 0.0, 13.2, 0.2, 10.9, 10.2, 14.1, 1.5, 9.5),
  count = c(14, 29, 16, 6, 45, 3, 13, 30, 57, 51, 31, 23,
            28, 24, 14, 8, 20, 4, 9, 25, 36, 25, 28, 14,
            2, 7, 3, 1, 21, 3, 5, 12, 19, 14, 9, 11,
            3, 1, 1, 5, 2, 1, 6, 6, 8, 6, 11, 2,
            3, 0, 0, 0, 0, 1, 1, 7, 6, 4, 2, 4)
)

p1 <- ggplot(totals, aes(x = person, y = content_k/1000, fill = person)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = paste0(round(content_k/sum(content_k)*100, 1), "%")), vjust = -0.5, size = 3) +
  scale_fill_manual(values = colors) +
  labs(title = "Total Email Content Written", y = "Characters (millions)", x = "") +
  theme_minimal() +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1))

p2 <- ggplot(totals, aes(x = person, y = emails_sent, fill = person)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = emails_sent), vjust = -0.5, size = 3) +
  scale_fill_manual(values = colors) +
  labs(title = "Total Emails Sent", y = "Count", x = "") +
  theme_minimal() +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1))

p3 <- ggplot(monthly, aes(x = month, y = chars_k, color = person, group = person)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = colors) +
  labs(title = "Monthly Email Content (2025-2026)", y = "Characters (k)", x = "Month", color = "") +
  theme_minimal() +
  theme(legend.position = "bottom")

p4 <- ggplot(monthly, aes(x = month, y = count, color = person, group = person)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = colors) +
  labs(title = "Monthly Email Count (2025-2026)", y = "Emails Sent", x = "Month", color = "") +
  theme_minimal() +
  theme(legend.position = "bottom")

combined <- (p1 + p2) / (p3 + p4) +
  plot_annotation(title = "EMAIL CONTRIBUTION ANALYSIS",
                  subtitle = "wenbin.wu@rhul.ac.uk | Feb 2024 - Jan 2026",
                  theme = theme(plot.title = element_text(face = "bold", size = 14)))

ggsave("email_contribution.png", combined, width = 14, height = 10, dpi = 150)
cat("Saved email_contribution.png\n")
