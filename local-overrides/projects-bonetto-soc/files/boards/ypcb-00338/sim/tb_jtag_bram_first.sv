// Fabric integration test. Inject commands at the bridge's SYS_CLK interface;
// the serial BSCAN path and physical cable are outside this simulation's scope.
`timescale 1ns/1ps
module tb_jtag_bram_first #(
    parameter integer FIRST_PROFILE = 1
);
    localparam integer BANK_WORDS = FIRST_PROFILE ? 1024 : 16384;
    localparam integer TEST_WORDS = FIRST_PROFILE ? 2 * BANK_WORDS : 8;
    localparam [31:0] VERSION_WORD = FIRST_PROFILE ? 32'hB07EB002 : 32'hB07EB001;
    reg clk = 0;
    reg rstn = 0;
    reg [31:0] command_word = 0;
    reg command_valid = 0;
    wire [2:0] leds;
    wire rst, jwb_busy, jwb_last_ack, jwb_last_err;
    wire [31:0] status_word;
    generate
        if (FIRST_PROFILE) begin : first_profile
            top_jtag_bram_first dut(.SYS_CLK(clk), .SYS_RSTN(rstn), .led_3bits_tri_o(leds));
            initial begin
                force dut.u_proof.host_to_fpga = command_word;
                force dut.u_proof.host_to_fpga_valid = command_valid;
            end
            assign rst = dut.u_proof.rst;
            assign jwb_busy = dut.u_proof.jwb_busy;
            assign jwb_last_ack = dut.u_proof.jwb_last_ack;
            assign jwb_last_err = dut.u_proof.jwb_last_err;
            assign status_word = dut.u_proof.status_word;
        end else begin : default_profile
            // Use the module defaults, so a changed default width or version
            // cannot silently be hidden by a matching test override.
            top_jtag_bram dut(.SYS_CLK(clk), .SYS_RSTN(rstn), .led_3bits_tri_o(leds));
            initial begin
                force dut.host_to_fpga = command_word;
                force dut.host_to_fpga_valid = command_valid;
            end
            assign rst = dut.rst;
            assign jwb_busy = dut.jwb_busy;
            assign jwb_last_ack = dut.jwb_last_ack;
            assign jwb_last_err = dut.jwb_last_err;
            assign status_word = dut.status_word;
        end
    endgenerate
    always #10 clk = !clk;

    task tick(input integer count);
        repeat (count) begin @(posedge clk); #1; end
    endtask

    task command(input [7:0] op, input [23:0] payload);
        @(negedge clk);
        command_word = {op, payload};
        command_valid = 1;
        tick(1);
        @(negedge clk);
        command_valid = 0;
        tick(1);
    endtask

    task complete;
        integer n;
        begin
            n = 0;
            while (jwb_busy === 1'b1 && n < 20) begin tick(1); n = n + 1; end
            if (jwb_busy !== 1'b0 || jwb_last_ack !== 1'b1 || jwb_last_err !== 1'b0)
                $fatal(1, "Wishbone operation failed, timed out, or has unknown status");
        end
    endtask

    task check_status(input [7:0] index, input [31:0] expected);
        command(8'h00, {16'd0, index});
        if (status_word !== expected)
            $fatal(1, "Status %h: got %h, expected %h", index, status_word, expected);
    endtask

    task write_word(input [15:0] address, input [31:0] data, input [3:0] mask);
        command(8'he0, address);
        command(8'he1, 0);
        command(8'he2, {8'd0, data[15:0]});
        command(8'he3, {8'd0, data[31:16]});
        command(8'hf0, {20'd0, mask});
        command(8'he4, 0);
        complete();
    endtask

    task check_word(input [15:0] address, input [31:0] expected);
        command(8'he0, address);
        command(8'he5, 0);
        complete();
        // Read the same registered status mux that the host uses. This checks
        // the full 32-bit address echo, including its zero extension.
        check_status(8'h11, {16'd0, address});
        check_status(8'h13, expected);
        check_status(8'h10, 32'hAB100004);
    endtask

    function [15:0] test_address(input integer index);
        if (FIRST_PROFILE)
            test_address = index;
        else begin
            case (index)
                0: test_address = 0;
                1: test_address = 1;
                2: test_address = 16;
                3: test_address = BANK_WORDS - 1;
                4: test_address = BANK_WORDS;
                5: test_address = BANK_WORDS + 1;
                6: test_address = BANK_WORDS + 16;
                7: test_address = 2 * BANK_WORDS - 1;
                default: test_address = 16'hxxxx;
            endcase
        end
    endfunction

    integer a;
    reg [15:0] address;
    reg [31:0] pattern;
    initial begin
        tick(3);
        if (rst !== 1'b1) $fatal(1, "Power-on reset was not asserted");
        @(negedge clk); rstn = 1;
        tick(16390);
        if (rst !== 1'b0) $fatal(1, "Power-on reset never released or is unknown");
        check_status(8'hfe, VERSION_WORD);

        // Sweep every first-profile word and the default-profile boundaries.
        // Read after all writes to catch address truncation and bank aliasing.
        for (a = 0; a < TEST_WORDS; a = a + 1) begin
            address = test_address(a);
            pattern = ((address + 1) * 32'h9e3779b9) ^ 32'h13579bdf;
            write_word(address, pattern, 4'hf);
        end
        for (a = 0; a < TEST_WORDS; a = a + 1) begin
            address = test_address(a);
            pattern = ((address + 1) * 32'h9e3779b9) ^ 32'h13579bdf;
            check_word(address, pattern);
        end
        for (a = 32; a < 2 * BANK_WORDS; a = a + BANK_WORDS) begin
            write_word(a, 32'h11223344, 4'hf);
            write_word(a, 32'haabbccdd, 4'h5);
            check_word(a, 32'h11bb33dd);
            write_word(a, 32'hffffffff, 4'h0);
            check_word(a, 32'h11bb33dd);
            write_word(a, 32'haabbccdd, 4'ha);
            check_word(a, 32'haabbccdd);
        end
        $display("RESULT PASS: first_profile=%0d; %0d words; bank isolation; byte masks; status mux",
                 FIRST_PROFILE, TEST_WORDS);
        $finish;
    end
    initial begin #20000000; $fatal(1, "Integration simulation deadline"); end
endmodule
