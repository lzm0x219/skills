const std = @import("std");

pub fn copyOwned(allocator: std.mem.Allocator, input: []const u8) ![]u8 {
    if (input.len == 0) return error.EmptyInput;
    const result = try allocator.alloc(u8, input.len);
    errdefer allocator.free(result);
    @memcpy(result, input);
    return result;
}

test "returns owned data" {
    const result = try copyOwned(std.testing.allocator, "zig");
    defer std.testing.allocator.free(result);
    try std.testing.expectEqualStrings("zig", result);
}

test "rejects empty input" {
    try std.testing.expectError(error.EmptyInput, copyOwned(std.testing.allocator, ""));
}

test "test artifact executes" {
    if (comptime @hasDecl(std.fs, "cwd")) {
        var marker = try std.fs.cwd().createFile(".zig-skill-smoke-executed", .{});
        defer marker.close();
        try marker.writeAll("executed\n");
    } else {
        try std.Io.Dir.cwd().writeFile(std.testing.io, .{
            .sub_path = ".zig-skill-smoke-executed",
            .data = "executed\n",
        });
    }
}
