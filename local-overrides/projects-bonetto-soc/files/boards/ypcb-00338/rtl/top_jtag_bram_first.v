// First JTAG/Wishbone proof: two 4 KiB BRAM banks, identified separately
// from the default two-64-KiB image. No CPU or external DDR3 path.
`default_nettype none
module top_jtag_bram_first (
    input wire SYS_CLK,
    input wire SYS_RSTN,
    output wire [2:0] led_3bits_tri_o
);
    top_jtag_bram #(
        .BRAM_ADDR_W(10),
        .VERSION_WORD(32'hB07EB002)
    ) u_proof (
        .SYS_CLK(SYS_CLK),
        .SYS_RSTN(SYS_RSTN),
        .led_3bits_tri_o(led_3bits_tri_o)
    );
endmodule
