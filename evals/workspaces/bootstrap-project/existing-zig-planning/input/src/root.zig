pub const answer: u8 = 42;

test "answer" {
    const std = @import("std");
    try std.testing.expectEqual(@as(u8, 42), answer);
}
