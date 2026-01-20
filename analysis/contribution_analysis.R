library(ggplot2)
library(dplyr)
library(tidyr)
library(patchwork)

theme_econ <- theme_bw(base_size = 10, base_family = "serif") +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.border = element_rect(color = "black", linewidth = 0.5),
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    axis.ticks = element_line(color = "black", linewidth = 0.3),
    axis.text = element_text(color = "black", size = 8),
    axis.title = element_text(color = "black", size = 9),
    plot.title = element_text(face = "plain", size = 10, hjust = 0.5),
    legend.background = element_blank(),
    legend.key = element_blank(),
    legend.text = element_text(size = 8),
    legend.title = element_blank(),
    legend.position = "bottom",
    strip.background = element_blank(),
    strip.text = element_text(face = "bold")
  )

email_people <- c("Wenbin Wu", "Mariol Jonuzaj", "Alessio Sancetta", "Francesco Feri", "Michael Naef")
email_colors <- c("black", "gray50", "gray70", "gray85", "gray95")
code_people <- c("Wenbin Wu", "Philipp Chapkovski", "Mariol Jonuzaj")
code_colors <- c("black", "gray50", "gray75")
paper_people <- c("Wenbin Wu", "Mariol Jonuzaj", "Alessio Sancetta")
paper_colors <- c("black", "gray50", "gray75")

email_totals <- data.frame(
  person = factor(email_people, levels = email_people),
  content_k = c(13026.9, 4784.9, 2520.9, 650.6, 212.4)
)

code_totals <- data.frame(
  person = factor(code_people, levels = code_people),
  lines = c(86315, 7775, 2365)
)

paper_totals <- data.frame(
  person = factor(paper_people, levels = paper_people),
  lines = c(3552, 761, 109)
)

email_months <- c("Feb25", "Mar25", "Apr25", "May25", "Jun25", "Jul25", "Aug25", "Sep25", "Oct25", "Nov25", "Dec25", "Jan26")
email_monthly <- data.frame(
  month = factor(rep(email_months, 5), levels = email_months),
  person = factor(rep(email_people, each = 12), levels = email_people),
  chars_k = c(29.2, 108.9, 37.6, 15.7, 133.1, 1.6, 23.5, 103.9, 96.8, 170.3, 74.7, 81.9,
              66.3, 133.3, 41.7, 18.6, 44.6, 4.6, 19.1, 92.1, 78.4, 85.8, 119.2, 60.5,
              2.9, 11.1, 1.6, 3.2, 60.4, 2.8, 13.6, 18.7, 28.7, 26.8, 30.5, 46.0,
              8.0, 1.5, 0.7, 9.5, 3.2, 1.1, 16.7, 42.9, 23.5, 17.3, 49.8, 18.4,
              4.5, 0.0, 0.0, 0.0, 0.0, 13.2, 0.2, 10.9, 10.2, 14.1, 1.5, 9.5)
)

code_months <- c("Aug23", "Sep23", "Nov23", "Dec23", "Jan24", "Feb24", "Mar24", "Apr24", 
                 "May24", "Jun24", "Jul24", "Aug24", "Sep24", "Oct24", "Nov24", "Dec24",
                 "Jan25", "Feb25", "Mar25", "Apr25", "May25", "Jun25", "Aug25", "Sep25", 
                 "Oct25", "Nov25", "Dec25", "Jan26")
code_monthly <- data.frame(
  month = factor(rep(code_months, 3), levels = code_months),
  person = factor(rep(code_people, each = 28), levels = code_people),
  commits = c(0, 0, 0, 0, 0, 3, 10, 9, 17, 10, 68, 28, 48, 65, 58, 2, 12, 11, 20, 4, 8, 45, 11, 8, 14, 13, 22, 9,
              13, 36, 14, 2, 3, 20, 36, 12, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 16, 11, 9, 10, 0, 1, 11, 3, 4, 0, 3, 6, 4, 0, 0)
)

paper_months <- c("Oct25", "Nov25", "Dec25", "Jan26")
paper_monthly <- data.frame(
  month = factor(rep(paper_months, 3), levels = paper_months),
  person = factor(rep(paper_people, each = 4), levels = paper_people),
  lines = c(651, 461, 2415, 25,
            629, 54, 19, 59,
            0, 0, 0, 109)
)

p1 <- ggplot(email_totals, aes(x = person, y = content_k/1000, fill = person)) +
  geom_bar(stat = "identity", width = 0.6, color = "black", linewidth = 0.3) +
  geom_text(aes(label = paste0(round(content_k/sum(content_k)*100, 1), "%")), vjust = -0.4, size = 2.8, family = "serif") +
  scale_fill_manual(values = email_colors) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "A. Email Content", y = "Characters (millions)", x = "") +
  theme_econ +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1, size = 7))

p2 <- ggplot(code_totals, aes(x = person, y = lines/1000, fill = person)) +
  geom_bar(stat = "identity", width = 0.6, color = "black", linewidth = 0.3) +
  geom_text(aes(label = paste0(round(lines/sum(lines)*100, 1), "%")), vjust = -0.4, size = 2.8, family = "serif") +
  scale_fill_manual(values = code_colors) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "B. Code Lines", y = "Lines (thousands)", x = "") +
  theme_econ +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1, size = 7))

p3 <- ggplot(paper_totals, aes(x = person, y = lines, fill = person)) +
  geom_bar(stat = "identity", width = 0.6, color = "black", linewidth = 0.3) +
  geom_text(aes(label = paste0(round(lines/sum(lines)*100, 1), "%")), vjust = -0.4, size = 2.8, family = "serif") +
  scale_fill_manual(values = paper_colors) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "C. Paper Changes", y = "Lines changed", x = "") +
  theme_econ +
  theme(legend.position = "none", axis.text.x = element_text(angle = 45, hjust = 1, size = 7))

p4 <- ggplot(email_monthly, aes(x = month, y = chars_k, linetype = person, shape = person, group = person)) +
  geom_line(linewidth = 0.5) + geom_point(size = 1.5) +
  scale_linetype_manual(values = c("solid", "dashed", "dotted", "dotdash", "longdash")) +
  scale_shape_manual(values = c(16, 17, 15, 3, 4)) +
  labs(title = "D. Email: Monthly Content", y = "Characters (k)", x = "") +
  theme_econ +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, size = 6),
        legend.key.width = unit(0.8, "cm"),
        legend.position = c(0.02, 0.98),
        legend.justification = c(0, 1),
        legend.background = element_rect(fill = "white", color = NA),
        legend.text = element_text(size = 6)) +
  guides(linetype = guide_legend(ncol = 2), shape = guide_legend(ncol = 2))

p5 <- ggplot(code_monthly, aes(x = month, y = commits, linetype = person, shape = person, group = person)) +
  geom_line(linewidth = 0.5) + geom_point(size = 1.5) +
  scale_linetype_manual(values = c("solid", "dashed", "dotted")) +
  scale_shape_manual(values = c(16, 17, 15)) +
  labs(title = "E. Code: Monthly Commits", y = "Commits", x = "") +
  theme_econ +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, size = 5),
        legend.key.width = unit(0.8, "cm"),
        legend.position = c(0.02, 0.98),
        legend.justification = c(0, 1),
        legend.background = element_rect(fill = "white", color = NA),
        legend.text = element_text(size = 6)) +
  guides(linetype = guide_legend(ncol = 1), shape = guide_legend(ncol = 1))

p6 <- ggplot(paper_monthly, aes(x = month, y = lines, linetype = person, shape = person, group = person)) +
  geom_line(linewidth = 0.5) + geom_point(size = 1.8) +
  scale_linetype_manual(values = c("solid", "dashed", "dotted")) +
  scale_shape_manual(values = c(16, 17, 15)) +
  labs(title = "F. Paper: Monthly Changes", y = "Lines changed", x = "") +
  theme_econ +
  theme(legend.key.width = unit(0.8, "cm"),
        legend.position = c(0.02, 0.98),
        legend.justification = c(0, 1),
        legend.background = element_rect(fill = "white", color = NA),
        legend.text = element_text(size = 6)) +
  guides(linetype = guide_legend(ncol = 1), shape = guide_legend(ncol = 1))

combined <- (p1 | p2 | p3) / (p4 | p5 | p6)

ggsave("contribution_analysis.png", combined, width = 14, height = 10, dpi = 150)
cat("Saved contribution_analysis.png\n")
