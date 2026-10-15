// Fabric integration test. Inject commands at the bridge's SYS_CLK interface;
// the serial BSCAN path and physical cable are outside this simulation's scope.
`timescale 1ns/1ps
module tb_jtag_bram_first;
    reg clk = 0;
    reg rstn = 0;
    reg [31:0] command_word = 0;
    reg command_valid = 0;
    wire [2:0] leds;
    top_jtag_bram_first dut(.SYS_CLK(clk), .SYS_RSTN(rstn), .led_3bits_tri_o(leds));
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
            while (dut.u_proof.jwb_busy && n < 20) begin tick(1); n = n + 1; end
            if (dut.u_proof.jwb_busy || !dut.u_proof.jwb_last_ack || dut.u_proof.jwb_last_err)
                $fatal(1, "Wishbone operation failed or timed out");
        end
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
        if (dut.u_proof.jwb_rd_data !== expected)
            $fatal(1, "Read %h: got %h, expected %h", address, dut.u_proof.jwb_rd_data, expected);
    endtask

    integer a;
    reg [31:0] pattern;
    initial begin
        force dut.u_proof.host_to_fpga = command_word;
        force dut.u_proof.host_to_fpga_valid = command_valid;
        tick(3);
        @(negedge clk); rstn = 1;
        tick(16390);
        if (dut.u_proof.rst) $fatal(1, "Power-on reset never released");
        @(negedge clk); command_word = 32'hfe;
        tick(3);
        if (dut.u_proof.status_word !== 32'hb07eb002)
            $fatal(1, "First-profile version mismatch");

        // Every word gets a distinct value. Reading after all writes catches
        // truncation, end-of-bank wraparound and cross-bank aliasing.
        for (a = 0; a < 2048; a = a + 1) begin
            pattern = ((a + 1) * 32'h9e3779b9) ^ 32'h13579bdf;
            write_word(a, pattern, 4'hf);
        end
        for (a = 0; a < 2048; a = a + 1) begin
            pattern = ((a + 1) * 32'h9e3779b9) ^ 32'h13579bdf;
            check_word(a, pattern);
        end
        for (a = 32; a < 2048; a = a + 1024) begin
            write_word(a, 32'h11223344, 4'hf);
            write_word(a, 32'haabbccdd, 4'h5);
            check_word(a, 32'h11bb33dd);
            write_word(a, 32'hffffffff, 4'h0);
            check_word(a, 32'h11bb33dd);
            write_word(a, 32'haabbccdd, 4'ha);
            check_word(a, 32'haabbccdd);
        end
        $display("RESULT PASS: first-profile fabric; all 2048 words; bank isolation; byte masks");
        $finish;
    end
    initial begin #20000000; $fatal(1, "Integration simulation deadline"); end
endmodule
